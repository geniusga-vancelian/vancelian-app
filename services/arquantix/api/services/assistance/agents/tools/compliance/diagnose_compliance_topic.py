"""Tool ``diagnose_compliance_topic`` — agent **compliance**, autonomy **L0**.

Pièce centrale du dispatcher Phase 2b. Appelé en **iter 0 forcée** par
le runtime compliance, il agrège les signaux DB existants et retourne
le `dominant_topic` parmi 4 :

    {registration | remediation | transactional | general}

Le runtime utilise ensuite ce topic pour basculer l'`agent_id` du
loop courant vers le sub-agent correspondant (`compliance.<topic>`),
charger son sous-prompt et restreindre son set de tools.

Cf. `docs/arquantix/COMPLIANCE_TOPICS.md` § 2.

──────────────────────────────────────────────────────────────────────
Garanties anti-tipping-off
──────────────────────────────────────────────────────────────────────

  - Le payload retourné contient **uniquement** :
      * des champs publics (déjà visibles dans l'UI mobile : kyc_status,
        account_state, registration steps, count d'orders) ;
      * le `next_recommended_action` qui propose un deep-link de la
        whitelist `action_cta_catalog`.
  - Aucun signal interne (`risk_score`, `level`, AML hits…) n'est
    exposé. La cascade de classification utilise les signaux gated
    via `compliance_repo.fetch_safe_signals` (déjà neutralisés).

──────────────────────────────────────────────────────────────────────
Convention de retour
──────────────────────────────────────────────────────────────────────

```
{
  "dominant_topic": "registration" | "remediation" | "transactional" | "general",
  "confidence": 0.0..1.0,
  "secondary_topics": list[str],
  "next_recommended_action": dict | null,
  "context_for_llm": dict,
  "triggers_used": list[str],
}
```

`next_recommended_action` est un dict `{kind, label, deep_link}` issu
de `action_cta_catalog.build_action()` (donc whitelisté), ou `None`
si aucune action n'est pertinente.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import action_cta_catalog

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "diagnose_compliance_topic",
        "description": (
            "Détermine le sous-univers Compliance pertinent pour ce "
            "client à ce moment, en agrégeant les signaux DB "
            "(registration, KYC, transactions, documents). Retourne le "
            "topic dominant, l'action recommandée à proposer au client "
            "(deep-link mobile), et le contexte exploitable par le LLM. "
            "À appeler en PREMIER dans toute conversation compliance. "
            "Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_message_hint": {
                    "type": "string",
                    "description": (
                        "Question utilisateur (ou résumé) — utile pour "
                        "départager registration vs transactional quand "
                        "l'état client le permet. Optionnel."
                    ),
                    "maxLength": 500,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance",
}


# Mots-clés FR/EN détectant une question transactionnelle. Liste
# volontairement restreinte (high-precision over recall) — en cas de
# doute on tombe sur `general`, pas sur transactional.
#
# Note pluriels : `\b` ne fait PAS de frontière entre deux word chars,
# donc `\bd[ée]p[oô]t\b` ne matchait pas « dépôts ». On ajoute `s?` à
# chaque mot pluralisable (FR et EN) — sinon une question parfaitement
# transactionnelle (« liste tous mes dépôts ») retombe sur `general`
# qui n'a pas `list_transactions` → mauvais format de réponse.
#
# Phase 2c.7 — Patch D : extension stats / portefeuille.
# Le sub-agent `compliance.transactional` est seul à porter les tools
# `stats_*` (`stats_transaction_counts`, `stats_transaction_amounts`,
# `stats_portfolio_performance`, `stats_portfolio_allocation`). Sans
# ces keywords, des questions comme « quelle est ma performance ? » ou
# « bilan de mes dépôts » tombent sur `compliance.general` (filet de
# sécurité ajouté en Lot 2) — qui répond, mais en sortie générique
# texte au lieu d'utiliser les widgets dédiés (table Markdown ou donut).
# Ajoutons-les ici pour router au bon sub-agent dès le tour 1.
#
# Mots-clés ajoutés (FR/EN) :
#   - perf / performance(s) / rendement(s)
#   - stats / statistique(s) / bilan(s)
#   - compter / combien (intent count)
#   - total / totaliser / totaux (intent amounts)
#   - allocation(s) / portefeuille(s) / portfolio (intent portfolio)
#
# « bilan » seul reste ambigu (« bilan compte » vs « bilan portefeuille »)
# — mais c'est OK : le sub-agent `transactional` a une règle de prompt
# explicite (Patch B.1 livré précédemment) qui le détecte et déclenche
# une clarification QCM avec `ask_user_question`.
_TRANSACTIONAL_KEYWORDS_RE = re.compile(
    r"\b(?:"
    r"transactions?|"
    r"d[ée]p[oô]ts?|d[ée]poser|d[ée]pos[eé]s?|"
    r"virements?|virer|"
    r"retraits?|retirer|"
    r"investissements?|investir|investis?|"
    r"op[ée]rations?|"
    r"deposits?|withdrawals?|transfers?|"
    r"orders?|trades?|"
    r"swaps?|achats?|ventes?|achet[eé]e?s?|vend[uu]e?s?|"
    r"historiques?|"
    # Phase 2c.7 — stats / portfolio
    r"performances?|perfs?|"
    r"rendements?|"
    r"statistiques?|stats?|"
    r"bilans?|"
    r"compter|combien|"
    r"totaux|totaliser|totals?|"
    r"allocations?|"
    r"portefeuilles?|portfolios?"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


# Mots-clés FR/EN détectant une question de **régularisation** /
# justificatifs / documents demandés / pourquoi une nouvelle action
# admin est requise.
#
# Liste **précise** : on évite les mots trop génériques (« vérifier »,
# « vérification ») qui s'appliquent aussi à transactional. Si un mot
# borderline est ajouté, il faut s'assurer que la cascade priorise
# correctement (is_tx > is_rem-keyword, voir `_classify`).
_REMEDIATION_KEYWORDS_RE = re.compile(
    r"\b(?:"
    r"justificatif|justificatifs|justifier|justifie|justification|"
    r"document|documents|documentation|"
    r"pi[èe]ce|pi[èe]ces|"
    r"preuve|preuves|"
    r"attestation|attestations|"
    r"r[ée]gularis(?:e|er|[eé][rs]?|ation)|"
    r"compl[ée]ment|compl[ée]mentaire|"
    r"upload|uploader|t[ée]l[ée]charger|fournir|"
    r"document[s]?\s+manquant|"
    r"demande[r]?\s+(?:un|encore|de\s+nouveau|à\s+nouveau)|"
    r"pourquoi.*(?:demand|justif|document|preuve|pi[èe]ce)|"
    r"why.*(?:request|require|provide|document|proof)"
    r")\b",
    re.IGNORECASE | re.UNICODE,
)


_SUSPENDED_ACCOUNT_STATES = frozenset({"PARTIAL", "BLOCKED"})


def _is_registration_pending(client_status: dict[str, Any], registration: dict[str, Any]) -> bool:
    """Indique si le client est encore en phase d'inscription/KYC."""
    kyc_status = client_status.get("kyc_status")
    account_state = client_status.get("account_state")
    completed = registration.get("completed_steps") or 0
    total = registration.get("total_steps_recorded") or 0
    if kyc_status is not None and kyc_status != "approved":
        return True
    if account_state in _SUSPENDED_ACCOUNT_STATES:
        return True
    if total > 0 and completed < total:
        return True
    return False


def _has_remediation_signals(
    client_status: dict[str, Any],
    safe_signals: dict[str, Any],
    documents: dict[str, Any],
    user_hint: str = "",
) -> tuple[bool, bool, list[str]]:
    """Indique si le client a un signal de régularisation.

    Retourne :
        (any_signal, has_db_signal, triggers)

    - ``any_signal`` : au moins un signal DB OU keyword.
    - ``has_db_signal`` : True si signal DB présent (utilisé par la
      cascade pour prioriser remediation sur transactional quand le
      DB indique objectivement une régularisation en cours).
    - ``triggers`` : liste des labels pour observabilité.

    Anti-tipping-off : aucun signal interne n'est répercuté en clair —
    seul le booléen et le label de trigger (générique :
    ``user_message_keyword_match``) sont utilisés en aval.
    """
    triggers: list[str] = []
    has_db_signal = False
    # Signaux DB (pertinents seulement si KYC approved & account ACTIVE).
    if client_status.get("kyc_status") == "approved" and client_status.get(
        "account_state"
    ) in (None, "ACTIVE"):
        if safe_signals.get("requires_doc_upload"):
            triggers.append("requires_doc_upload=true")
            has_db_signal = True
        if safe_signals.get("requires_step_up"):
            triggers.append("requires_step_up=true")
            has_db_signal = True
        by_status = documents.get("by_status") or {}
        if by_status.get("rejected", 0) > 0:
            triggers.append("documents_rejected_present")
            has_db_signal = True
    # Signal explicite via question utilisateur (indépendant du KYC :
    # un client peut poser la question même en cours d'onboarding).
    if user_hint and _REMEDIATION_KEYWORDS_RE.search(user_hint):
        triggers.append("user_message_keyword_match")
    return (len(triggers) > 0, has_db_signal, triggers)


def _is_transactional_question(
    user_hint: str, transactions: dict[str, Any]
) -> tuple[bool, list[str]]:
    """True si la question pointe une opération OU si transactions récentes anormales.

    Retourne aussi la liste de triggers détectés (pour observabilité).
    """
    triggers: list[str] = []
    if user_hint and _TRANSACTIONAL_KEYWORDS_RE.search(user_hint):
        triggers.append("user_message_keyword_match")
    by_status = transactions.get("by_status") or {}
    if by_status.get("failed", 0) > 0 or by_status.get("rejected", 0) > 0:
        triggers.append("recent_failed_transactions")
    return (len(triggers) > 0, triggers)


def _build_recommended_action(
    *,
    topic: str,
    client_status: dict[str, Any],
    transactions: dict[str, Any],
    registration: dict[str, Any],
) -> Optional[dict[str, str]]:
    """Construit la `next_recommended_action` selon le topic + état.

    Retourne `None` si aucune action évidente. Toujours via
    `action_cta_catalog.build_action()` pour respecter la whitelist.
    """
    # REGISTRATION — proposer la reprise si on a une session active.
    if topic == "registration":
        if registration.get("session_status") in (
            "in_progress",
            "started",
            "active",
            "open",
        ) or registration.get("current_step_id"):
            return action_cta_catalog.build_action("resume_registration")
        # Fallback si KYC approved mais étapes restantes : renvoyer
        # vers le dépôt si 0 order (incitation premier dépôt).
        if (
            client_status.get("kyc_status") == "approved"
            and (transactions.get("orders_count") or 0) == 0
        ):
            return action_cta_catalog.build_action("deposit_funds")
        return None

    # REMEDIATION — pas de deep-link upload doc tant qu'écran Flutter
    # n'existe pas. On propose `view_account_info` comme entrée en matière.
    if topic == "remediation":
        return action_cta_catalog.build_action("view_account_info")

    # TRANSACTIONAL — selon données : voir les transactions globales si
    # plusieurs orders, sinon déposer si 0 order.
    if topic == "transactional":
        if (transactions.get("orders_count") or 0) > 0:
            return action_cta_catalog.build_action("view_transactions")
        return action_cta_catalog.build_action("deposit_funds")

    # GENERAL — pas d'action proactive.
    return None


def _classify(
    *,
    client_status: dict[str, Any],
    safe_signals: dict[str, Any],
    registration: dict[str, Any],
    documents: dict[str, Any],
    transactions: dict[str, Any],
    user_hint: str,
) -> tuple[str, float, list[str], list[str]]:
    """Cascade de classification. Premier matché gagne.

    Returns:
        (dominant_topic, confidence, secondary_topics, triggers_used)
    """
    triggers: list[str] = []
    secondary: list[str] = []

    is_reg = _is_registration_pending(client_status, registration)
    is_rem, has_rem_db, rem_triggers = _has_remediation_signals(
        client_status, safe_signals, documents, user_hint=user_hint
    )
    is_tx, tx_triggers = _is_transactional_question(user_hint, transactions)

    # ── 1. Registration prioritaire ──────────────────────────────
    if is_reg:
        if client_status.get("kyc_status") and client_status.get("kyc_status") != "approved":
            triggers.append(f"kyc_status={client_status['kyc_status']}")
        if client_status.get("account_state") in _SUSPENDED_ACCOUNT_STATES:
            triggers.append(f"account_state={client_status['account_state']}")
        if (registration.get("total_steps_recorded") or 0) > 0:
            triggers.append(
                f"registration_steps={registration.get('completed_steps')}/{registration.get('total_steps_recorded')}"
            )
        if is_rem:
            secondary.append("remediation")
            triggers.extend(rem_triggers)
        if is_tx:
            secondary.append("transactional")
            triggers.extend(tx_triggers)
        return ("registration", 0.85, secondary, triggers)

    # ── 2. Remediation par signal DB explicite ───────────────────
    # Quand le DB indique objectivement une régularisation à faire
    # (doc upload requis, doc rejeté, step-up demandé), c'est plus
    # fiable que n'importe quel keyword utilisateur.
    if has_rem_db:
        triggers.extend(rem_triggers)
        if is_tx:
            secondary.append("transactional")
            triggers.extend(tx_triggers)
        return ("remediation", 0.8, secondary, triggers)

    # ── 3. Transactional (keyword TX OU failed) ──────────────────
    # Avant les remediation purement keyword : si le user mentionne
    # explicitement « transactions », « dépôt », « virement », etc.,
    # c'est un signal sur-précis (high precision) qui doit gagner sur
    # une co-occurrence keyword remediation type « justificatif ».
    if is_tx:
        triggers.extend(tx_triggers)
        # Si user_hint évoque AUSSI remediation (« vérifier mes
        # justificatifs de transactions ») on log secondary pour que
        # le sub-agent transactional puisse adapter sa réponse.
        if is_rem:
            secondary.append("remediation")
            # Évite duplication : on ne re-rajoute que si pas déjà.
            for t in rem_triggers:
                if t not in triggers:
                    triggers.append(t)
        # Confiance : 0.75 si données transactionnelles existent,
        # 0.6 sinon (le user pose la question mais 0 transaction →
        # ambiguïté possible avec onboarding "premier dépôt").
        confidence = 0.75 if (transactions.get("orders_count") or 0) > 0 else 0.6
        return ("transactional", confidence, secondary, triggers)

    # ── 4. Remediation par keyword utilisateur uniquement ────────
    # Plus faible confiance — le user a parlé de « justificatif » /
    # « document » sans qu'il n'y ait aucun signal DB.
    if is_rem:
        triggers.extend(rem_triggers)
        return ("remediation", 0.7, secondary, triggers)

    # ── 5. Fallback ──────────────────────────────────────────────
    triggers.append("no_specific_signal")
    return ("general", 0.5, secondary, triggers)


def execute(
    ctx: ToolContext, *, user_message_hint: str = "", **_kwargs: Any
) -> dict[str, Any]:
    """Aggrège les 4 signaux et classe en cascade.

    Best-effort : tout échec de repo retourne un payload partiel valide
    (jamais d'exception remontée).
    """
    user_hint = (user_message_hint or "")[:500].strip()

    # Aggrégation parallèle des signaux. Chaque repo est best-effort.
    try:
        snapshot = compliance_repo.fetch_compliance_state_snapshot(
            ctx.db, client_id=ctx.client_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "diagnose.snapshot_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        snapshot = {"status": {}, "safe_signals": {}}

    client_status = snapshot.get("status") or {}
    safe_signals = snapshot.get("safe_signals") or {}

    try:
        registration = compliance_repo.fetch_registration_progress(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "diagnose.registration_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        registration = {}

    try:
        documents = compliance_repo.fetch_documents_summary(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "diagnose.documents_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        documents = {}

    try:
        transactions = compliance_repo.fetch_transactions_summary(
            ctx.db, client_id=ctx.client_id, limit=10
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "diagnose.transactions_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        transactions = {}

    topic, confidence, secondary, triggers = _classify(
        client_status=client_status,
        safe_signals=safe_signals,
        registration=registration,
        documents=documents,
        transactions=transactions,
        user_hint=user_hint,
    )

    next_action = _build_recommended_action(
        topic=topic,
        client_status=client_status,
        transactions=transactions,
        registration=registration,
    )

    # Contexte LLM-friendly (champs publics seulement, anti-tipping-off).
    context_for_llm = {
        "kyc_complete": client_status.get("kyc_status") == "approved",
        "kyc_status": client_status.get("kyc_status"),
        "account_state": client_status.get("account_state"),
        "registration_completed_steps": registration.get("completed_steps") or 0,
        "registration_total_steps": registration.get("total_steps_recorded") or 0,
        "documents_total": documents.get("total_count") or 0,
        "documents_by_status": documents.get("by_status") or {},
        "orders_count": transactions.get("orders_count") or 0,
        "first_deposit_done": (transactions.get("orders_count") or 0) > 0,
    }

    logger.info(
        "diagnose_compliance_topic conv=%s topic=%s conf=%.2f triggers=%s",
        ctx.conversation_id,
        topic,
        confidence,
        triggers,
    )

    return {
        "dominant_topic": topic,
        "confidence": round(confidence, 2),
        "secondary_topics": secondary,
        "next_recommended_action": next_action,
        "context_for_llm": context_for_llm,
        "triggers_used": triggers,
    }
