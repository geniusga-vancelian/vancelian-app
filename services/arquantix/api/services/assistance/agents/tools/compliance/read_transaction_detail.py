"""Tool ``read_transaction_detail`` — agent **compliance.transactional**, autonomy **L0**.

Détail safe d'une transaction précise par ID. Vérifie l'ownership
côté repo (la transaction doit appartenir au `client_id` courant) ;
sinon retourne `error=not_found` (jamais `forbidden` pour ne pas
révéler l'existence d'un order tiers).

Phase 2b : retour minimal au LLM (status, kind, dates) — pas de
montants bruts ni contrepartie.

Phase 2c.2 : embed UI structuré dans `ctx.embeds_to_emit` rendu par
``TransactionDetailEmbed`` côté Flutter avec actions
*Voir la transaction* / *Télécharger le relevé*.

Phase 2c.4 : **fusion en un seul module visuel**. L'embed contient
désormais une clé ``summary`` — un récap textuel court (1 phrase
chaleureuse + mention du problème uniquement si statut ≠ completed)
composé côté serveur. Cela permet au widget Flutter de rendre
**récap + tableau + liens** dans une seule bulle assistant, et le
prompt instruit le LLM à **ne rien écrire** dans son texte (la carte
se suffit).

Garantie anti-tipping-off : `amount` et `currency` lus depuis le repo
sont consommés **uniquement** pour le `summary` puis **strippés**
avant retour au LLM. Le LLM ne voit jamais le montant brut, même si
la composition du summary l'utilise. Le client mobile a déjà accès à
ces données via l'API authentifiée (``TransactionDetailApi``), le
summary ne révèle rien de nouveau côté UI.

Cf. `docs/arquantix/COMPLIANCE_TOPICS.md` § 3.3 et § 6.4 (embeds).
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import action_cta_catalog

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_transaction_detail",
        "description": (
            "Retourne le statut et le type d'une transaction précise du "
            "client courant (par ID opaque). Vérifie l'ownership : si "
            "l'ID n'appartient pas au client, retourne `not_found`. Ne "
            "remonte jamais de montant brut ni de PII contrepartie. "
            "Déclenche automatiquement l'affichage d'une carte de détail "
            "complète côté client (récap textuel + tableau de toutes les "
            "données + 2 boutons d'action). Tu DOIS te taire après cet "
            "appel : la carte contient TOUT, ne réécris ni intro ni "
            "résumé ni listing. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": (
                        "Identifiant opaque de la transaction (UUID). "
                        "Doit être obtenu via `read_transactions` "
                        "(`recent_order_ids`) ou `list_transactions` "
                        "(items[].id)."
                    ),
                    "minLength": 32,
                    "maxLength": 36,
                },
            },
            "required": ["transaction_id"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance.transactional",
}


# ─────────────────────────────────────────────────────────────────────
# Composition du `summary` (récap textuel chaleureux)
# ─────────────────────────────────────────────────────────────────────


# Action FR selon `kind` ou direction. Volontairement très restreint —
# toute valeur inconnue retombe sur "opération".
_ACTION_BY_KIND_INBOUND: dict[str, str] = {
    "bank_transfer_in": "dépôt par virement bancaire",
    "card_in": "dépôt par carte",
    "crypto_in": "dépôt en crypto",
    "deposit": "dépôt",
}

_ACTION_BY_KIND_OUTBOUND: dict[str, str] = {
    "bank_transfer_out": "virement sortant",
    "withdrawal": "retrait",
}

# Phrase de problème selon statut. `completed` = pas de phrase
# (on ne dit pas que tout va bien quand tout va bien — éviter le
# bruit textuel).
_STATUS_PROBLEM_FR: dict[str, str] = {
    "pending": " — actuellement en attente",
    "on_hold": " — actuellement bloqué pour vérification",
    "failed": " — qui a échoué",
    "rejected": " — qui a été rejeté",
    "cancelled": " — qui a été annulé",
}


_FR_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


_CURRENCY_SYMBOLS: dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CHF": "CHF",
}


def _format_amount(value: Decimal) -> str:
    """``45000.00`` → ``45 000`` (FR, sans décimales si entier propre,
    sinon 2 décimales). Espace fin (\u202f) entre milliers."""
    quantized = value.quantize(Decimal("0.01"))
    int_part, _, dec_part = f"{quantized:.2f}".partition(".")
    sign = ""
    if int_part.startswith("-"):
        sign = "-"
        int_part = int_part[1:]
    grouped: list[str] = []
    while len(int_part) > 3:
        grouped.append(int_part[-3:])
        int_part = int_part[:-3]
    grouped.append(int_part)
    int_fr = "\u202f".join(reversed(grouped))
    if dec_part == "00":
        return f"{sign}{int_fr}"
    return f"{sign}{int_fr},{dec_part}"


def _format_date_fr_long(iso: Optional[str]) -> Optional[str]:
    """ISO ``2026-05-03T02:34:00+00:00`` → ``3 mai 2026``."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return f"{dt.day} {_FR_MONTHS[dt.month - 1]} {dt.year}"


def _resolve_action_label(detail: dict[str, Any]) -> str:
    kind = (detail.get("kind") or "").lower()
    is_inbound = detail.get("is_inbound")
    table = (
        _ACTION_BY_KIND_INBOUND if is_inbound else _ACTION_BY_KIND_OUTBOUND
    )
    if kind in table:
        return table[kind]
    # Fallback générique selon direction.
    if is_inbound is True:
        return "dépôt"
    if is_inbound is False:
        return "retrait"
    return "opération"


def _compose_summary(detail: dict[str, Any]) -> Optional[str]:
    """Compose un récap textuel court à partir du détail.

    Cas typique (status=completed) :
        *« Tu as fait un dépôt par virement bancaire de 45 000 € le
        3 mai 2026. Voici les détails ci-dessous. »*

    Cas problème (status=pending) :
        *« Tu as fait un dépôt par virement bancaire de 45 000 € le
        3 mai 2026 — actuellement en attente. Voici les détails
        ci-dessous. »*

    Retourne `None` si on n'a pas assez de données pour composer une
    phrase utile (le widget retombe alors sur le rendu standard sans
    récap).
    """
    action = _resolve_action_label(detail)
    date_fr = _format_date_fr_long(detail.get("created_at"))

    raw_amount = detail.get("amount")
    amount_str: Optional[str] = None
    if raw_amount is not None:
        try:
            value = Decimal(str(raw_amount))
            currency = (detail.get("currency") or "EUR").upper()
            symbol = _CURRENCY_SYMBOLS.get(currency, currency)
            amount_str = f"{_format_amount(value)} {symbol}"
        except (InvalidOperation, TypeError):
            amount_str = None

    # Si on n'a NI date NI montant, le récap serait trop pauvre
    # (« Tu as fait une opération. Voici les détails ci-dessous. »)
    # — on s'abstient et on laisse la carte parler seule.
    if not date_fr and not amount_str:
        return None

    # Construction de la phrase principale (tutoiement, ton DS).
    parts: list[str] = ["Tu as fait un", action]
    if amount_str:
        parts.append(f"de {amount_str}")
    if date_fr:
        parts.append(f"le {date_fr}")
    head = " ".join(parts)

    status = (detail.get("status") or "").lower()
    suffix = _STATUS_PROBLEM_FR.get(status, "")

    return f"{head}{suffix}. Voici les détails ci-dessous."


# ─────────────────────────────────────────────────────────────────────
# Champs internes à NE PAS exposer au LLM (anti-tipping-off).
# ─────────────────────────────────────────────────────────────────────
_INTERNAL_ONLY_KEYS: frozenset[str] = frozenset({"amount", "currency"})


def _strip_internal(detail: dict[str, Any]) -> dict[str, Any]:
    """Retourne une copie du detail sans les clés internes."""
    return {k: v for k, v in detail.items() if k not in _INTERNAL_ONLY_KEYS}


# ─────────────────────────────────────────────────────────────────────
# Execute
# ─────────────────────────────────────────────────────────────────────


def execute(
    ctx: ToolContext, *, transaction_id: str, **_kwargs: Any
) -> dict[str, Any]:
    if not ctx.client_id:
        return {
            "transaction_id": transaction_id,
            "error": "no_client_context",
        }
    if not transaction_id:
        return {"error": "missing_transaction_id"}

    try:
        detail = compliance_repo.fetch_transaction_detail(
            ctx.db,
            client_id=ctx.client_id,
            transaction_id=transaction_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_transaction_detail.repo_error agent=%s conv=%s tid=%s",
            ctx.agent_id,
            ctx.conversation_id,
            transaction_id,
        )
        return {
            "transaction_id": transaction_id,
            "error": "repo_unavailable",
        }

    # Phase 2c.2 / 2c.4 — Embed UI riche (carte « tout-en-un »).
    if "error" not in detail:
        view_action = action_cta_catalog.build_action(
            "view_transaction_detail",
            params={"transaction_id": str(transaction_id)},
        )
        download_action = action_cta_catalog.build_action(
            "download_transaction_statement",
            params={"transaction_id": str(transaction_id)},
        )
        actions = [a for a in (view_action, download_action) if a is not None]
        embed: dict[str, Any] = {
            "type": "transaction_detail",
            "transaction_id": str(transaction_id),
            "actions": actions,
        }
        if detail.get("status"):
            embed["status"] = detail["status"]
        if detail.get("kind"):
            embed["kind"] = detail["kind"]
        if detail.get("is_inbound") is not None:
            embed["is_inbound"] = detail["is_inbound"]
        # Phase 2c.4 — récap chaleureux composé serveur. Vit dans
        # l'embed, jamais dans le tool result LLM.
        summary = _compose_summary(detail)
        if summary:
            embed["summary"] = summary
        ctx.embeds_to_emit.append(embed)

    # Anti-tipping-off : strip `amount` / `currency` avant retour LLM,
    # même si le repo les a fournis (on les a utilisés ci-dessus pour
    # composer le summary, ils n'ont rien à faire dans le contexte LLM).
    return _strip_internal(detail)
