"""Mémoire long-terme de l'assistance — Palier 2 D.2.

Module **autonome**, sans dépendance à `services.chatbot_epargne`. Il
implémente le mécanisme de « rolling summary » + extraction de faits
structurés + agrégation cross-conversations sur `pe_clients`.

Surface publique
================

- `count_tokens(messages, model)`            : compte les tokens via tiktoken.
- `should_consolidate(messages, threshold)`  : True si le contexte dépasse le
                                               seuil de tokens.
- `build_context(*, summary, client_long_memory, recent_turns)`
                                             : assemble le payload OpenAI
                                               (system + memory + recent).
- `consolidate_conversation(*, session_factory, conversation_id)`
                                             : tâche async post-réponse SSE
                                               qui consolide la mémoire d'une
                                               conversation et met à jour la
                                               mémoire client agrégée.

Complément **hors** de ce module mais voisin conceptuellement : les
dimensions **orchestrateur** du router (`orchestration` dans
``assistance_agent_decisions.arguments_json``, cf.
``agents/orchestration_context.py``) enrichissent l'audit « mémoire
comportementale » tour par tour sans doubler les faits client.

Toutes les autres fonctions sont privées (`_…`) et exposées uniquement pour
les tests d'intégration via le module.

Conventions
===========

- **Best-effort** : aucun échec ici ne doit rejaillir sur le tour client.
  Toutes les entrées sont catch-all loggées et le code retombe sur des
  valeurs neutres (pas de mémoire mise à jour, mais conv non bloquée).
- **JSON strict** : appels LLM en `response_format={"type": "json_object"}`,
  `temperature=0.2`, fallback heuristique en cas de retour non-parsable.
- **Idempotence** : on stocke `summarized_until_turn` pour ne pas
  re-compresser un tour déjà absorbé. Les consolidations concurrentes sur
  la même conv sont sérialisées via `_consolidation_locks`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from database import (
    AssistanceConversation,
    AssistanceMessage,
)
from services.assistance.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)
# Le modèle SQLAlchemy de la table `pe_clients` s'appelle `Client` côté
# code Python (cf. services.portfolio_engine.clients.models). On l'alias
# en `PeClients` localement pour aligner le vocabulaire avec la table SQL
# et le modèle Prisma `PeClients`.
from services.portfolio_engine.clients.models import Client as PeClients

logger = logging.getLogger(__name__)


# ── Configuration runtime ─────────────────────────────────────────────────


def assistance_summarizer_model() -> str:
    """Modèle utilisé pour le summarizer.

    Préfère `ASSISTANCE_SUMMARIZER_MODEL` (var dédiée), sinon retombe sur
    `OPENAI_MODEL` du chat principal. Défaut final = `gpt-4o-mini`.
    """
    return (
        os.getenv("ASSISTANCE_SUMMARIZER_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    )


def assistance_summary_threshold_tokens() -> int:
    """Seuil de déclenchement de la consolidation (en tokens).

    Au-delà, on compresse les anciens tours dans `conversation_summary` et
    on n'envoie plus que le résumé + les K derniers tours bruts.

    **Défaut 2500** (révisé 2026-05-04 depuis 6000) pour mieux servir le
    profil mobile : la majorité des sessions Vancelian font 10-30 tours
    sans dépasser 4000 tokens. Avec un seuil à 6000, ces conversations
    informatives ne contribuaient jamais à la mémoire long-terme client.
    À 2500, on consolide ~tous les 8-12 tours selon la verbosité — coût
    LLM marginal (`gpt-4o-mini` summarizer ≈ 0,001 USD / call) et gain
    UX réel (l'agent apprend du client à chaque session significative).

    Floor à 1000 préservé : valeurs sous ce seuil dégénèrent en
    consolidation à chaque tour, ce qui n'a pas de sens.
    """
    try:
        return max(1000, int(os.getenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "2500")))
    except ValueError:
        return 2500


def assistance_summary_min_turns() -> int:
    """Nombre de tours minimum déclenchant la consolidation indépendamment du seuil tokens.

    **Défaut 10** (introduit 2026-05-04). Raison : sur des conversations
    avec messages courts (questions QCM, choix simples), on peut
    accumuler 20-30 tours sans dépasser le seuil tokens — et donc ne
    jamais consolider. Ce trigger garantit qu'au-delà de N tours
    user/assistant complets, la mémoire est extraite quoi qu'il arrive.

    Conversion : 1 tour ≈ 2 messages (1 user + 1 assistant). Le
    déclencheur est donc ``len(messages) >= min_turns * 2``.

    Mettre ``ASSISTANCE_SUMMARY_MIN_TURNS=0`` pour désactiver ce trigger
    (ne garder que le seuil tokens, comportement < 2026-05-04).

    Floor à 0 (désactivation), ceiling à 200 (sécurité).
    """
    try:
        v = int(os.getenv("ASSISTANCE_SUMMARY_MIN_TURNS", "10"))
    except ValueError:
        return 10
    return max(0, min(200, v))


def assistance_recent_turns_kept() -> int:
    """K — nombre de derniers tours bruts à toujours envoyer (post-summary)."""
    try:
        return max(2, int(os.getenv("ASSISTANCE_RECENT_TURNS_KEPT", "8")))
    except ValueError:
        return 8


def assistance_summarizer_temperature() -> float:
    try:
        return max(0.0, min(2.0, float(os.getenv("ASSISTANCE_SUMMARIZER_TEMPERATURE", "0.2"))))
    except ValueError:
        return 0.2


# ── Comptage tokens ───────────────────────────────────────────────────────


def count_tokens(messages: Iterable[dict], model: str | None = None) -> int:
    """Compte les tokens d'une liste de messages OpenAI-style.

    Utilise `tiktoken` si disponible (encoding `cl100k_base` pour la famille
    gpt-4o). Si tiktoken n'est pas installé (cas pathologique build), retombe
    sur une heuristique 1 token ≈ 4 chars (suffisant pour le déclenchement
    du seuil — pas pour de la facturation).
    """
    model = model or assistance_summarizer_model()
    try:
        import tiktoken  # type: ignore

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        # Approximation OpenAI : ~3 tokens d'overhead par message + role.
        # Cf. https://platform.openai.com/docs/guides/text-generation/managing-tokens
        total = 0
        for msg in messages:
            content = msg.get("content", "") or ""
            role = msg.get("role", "") or ""
            total += 4  # overhead tokens / message
            total += len(encoding.encode(content))
            total += len(encoding.encode(role))
        total += 3  # overhead conversation
        return total
    except ImportError:
        logger.warning("tiktoken not installed, falling back to char heuristic")
        chars = sum(
            len((m.get("content") or "")) + len((m.get("role") or "")) + 8
            for m in messages
        )
        return chars // 4


def should_consolidate(
    messages: Iterable[dict],
    threshold: int | None = None,
    min_turns: int | None = None,
) -> bool:
    """True si on doit consolider la conversation.

    Deux déclencheurs (logique **OR**) :

    1. **Seuil tokens** (``threshold``, défaut
       ``assistance_summary_threshold_tokens()`` = 2500) — consolide
       quand le contexte dépasse ce volume pour libérer de la place
       dans la fenêtre LLM.
    2. **Seuil tours** (``min_turns``, défaut
       ``assistance_summary_min_turns()`` = 10) — consolide quand le
       nombre de messages atteint ``min_turns * 2`` (1 tour = 1 user +
       1 assistant), même si le contexte tient sous le seuil tokens.
       Garantit que les conversations longues mais peu verbeuses
       finissent par alimenter la mémoire long-terme.

    Args:
        messages: liste de messages OpenAI-style (``{"role", "content"}``).
        threshold: override token (utile pour tests). ``None`` →
            valeur courante de l'env.
        min_turns: override min_turns (utile pour tests). ``None`` →
            valeur courante de l'env. ``0`` désactive ce déclencheur.

    Returns:
        True si l'un des deux seuils est atteint.
    """
    threshold = threshold or assistance_summary_threshold_tokens()
    if min_turns is None:
        min_turns = assistance_summary_min_turns()
    msgs_list = list(messages)
    if min_turns > 0 and len(msgs_list) >= min_turns * 2:
        return True
    return count_tokens(msgs_list) >= threshold


# ── Assemblage du contexte envoyé à OpenAI ────────────────────────────────


def build_context(
    *,
    summary: str | None,
    client_long_memory: dict | None,
    recent_turns: list[dict],
) -> list[dict]:
    """Assemble le payload `messages` final pour OpenAI.

    Structure produite :
        [
          (le system prompt principal n'est PAS injecté ici — c'est
           l'appelant `services.assistance.llm` qui le préfixe.)
          {role: "system", content: "## Contexte client (cross-conv)\\n…\\n## Résumé conv en cours\\n…"},
          ...recent_turns
        ]

    Si ni `summary` ni `client_long_memory` ne contiennent de la donnée
    exploitable, le bloc memory n'est pas injecté → comportement identique
    à l'historique brut (compatible Palier 1).
    """
    messages: list[dict] = []

    memory_block = _format_memory_block(
        summary=summary, client_long_memory=client_long_memory
    )
    if memory_block:
        messages.append({"role": "system", "content": memory_block})

    messages.extend(recent_turns)
    return messages


def _format_memory_block(
    *, summary: str | None, client_long_memory: dict | None
) -> str | None:
    """Sérialise summary + client_long_memory en Markdown lisible LLM.

    Retourne None si rien d'utile à injecter, pour éviter du bruit.
    """
    parts: list[str] = []

    long_facts = (client_long_memory or {}).get("facts") or []
    if long_facts:
        bullets = []
        for f in long_facts:
            t = f.get("type") or "other"
            v = f.get("value")
            c = f.get("confidence")
            if v is None:
                continue
            line = f"- **{t}** : {v}"
            if isinstance(c, (int, float)) and c < 0.7:
                line += f" _(confiance {c:.1f})_"
            bullets.append(line)
        if bullets:
            parts.append(
                "## Contexte client (mémoire long-terme cross-conversations)\n"
                + "\n".join(bullets)
            )

    if summary and summary.strip():
        parts.append(
            "## Résumé de la conversation en cours\n" + summary.strip()
        )

    if not parts:
        return None
    return "\n\n".join(parts)


# ── Consolidation async post-réponse SSE ──────────────────────────────────


# Locks par conv_id pour sérialiser les consolidations concurrentes (ex.
# deux tours envoyés très vite sur la même conv). Garde-fou applicatif :
# pas un vrai lock distribué, mais suffisant pour 1 instance API. Si on
# scale horizontal, on passe à un advisory lock Postgres.
_consolidation_locks: dict[UUID, asyncio.Lock] = {}


def _lock_for(conv_id: UUID) -> asyncio.Lock:
    lock = _consolidation_locks.get(conv_id)
    if lock is None:
        lock = asyncio.Lock()
        _consolidation_locks[conv_id] = lock
    return lock


async def consolidate_conversation(
    *,
    session_factory,
    conversation_id: UUID,
) -> None:
    """Tâche async exécutée après le `done` SSE.

    Étapes :
      1. Charge la conversation, le client, et tous les messages.
      2. Décide si une consolidation est nécessaire (seuil tokens).
      3. Appelle le LLM summarizer sur les nouveaux tours.
      4. Persiste : `conversation_summary`, `conversation_facts`,
         `summarized_until_turn`, `summary_updated_at`.
      5. Met à jour `pe_clients.assistance_long_memory` (merge dédupliqué
         des nouveaux faits avec ceux déjà connus).

    Best-effort : tout échec est loggué en warning et n'interrompt pas le
    flux principal. La consolidation sera retentée au tour suivant.
    """
    lock = _lock_for(conversation_id)
    async with lock:
        try:
            await asyncio.to_thread(_consolidate_sync, session_factory, conversation_id)
        except Exception:  # noqa: BLE001 - best-effort, on log et on tait.
            # WARNING (pas exception) pour rester visible sans noise stack-trace
            # systématique en prod : on log la trace une fois pour diag, mais le
            # message principal est lisible directement dans `docker logs`.
            logger.warning(
                "assistance.memory.consolidation_failed conv=%s",
                conversation_id,
                exc_info=True,
            )


def _consolidate_sync(session_factory, conversation_id: UUID) -> None:
    """Implémentation synchrone (exécutée dans un thread via asyncio.to_thread).

    Utilise une session BDD courte, indépendante du flux principal. Les
    écritures sont commitées en une seule transaction pour atomicité.
    """
    db: Session = session_factory()
    try:
        conv = (
            db.query(AssistanceConversation)
            .filter(AssistanceConversation.id == conversation_id)
            .one_or_none()
        )
        if conv is None:
            logger.info(
                "consolidate skipped: conv gone conv=%s", conversation_id
            )
            return

        # Charge tous les messages dans l'ordre chronologique.
        all_messages = (
            db.query(AssistanceMessage)
            .filter(AssistanceMessage.conversation_id == conv.id)
            .order_by(AssistanceMessage.turn_index.asc())
            .all()
        )
        if len(all_messages) < 2:
            return  # rien à compresser

        # Décide du déclenchement : on ne consolide QUE si l'historique
        # complet dépasse le seuil. En-dessous, le payload tient sans
        # compression et on évite les coûts LLM inutiles.
        as_dicts = [{"role": m.role, "content": m.content} for m in all_messages]
        if not should_consolidate(as_dicts):
            return

        last_summarized = conv.summarized_until_turn or -1
        new_turns = [m for m in all_messages if m.turn_index > last_summarized]
        if not new_turns:
            return  # rien de nouveau à intégrer

        # Charge la mémoire client courante pour la passer en contexte au
        # summarizer (évite les doublons de faits déjà connus).
        client = (
            db.query(PeClients)
            .filter(PeClients.id == conv.client_id)
            .one_or_none()
        )
        client_memory: dict = (
            client.assistance_long_memory if client is not None else {}
        ) or {}

        # Appel LLM summarizer — best-effort.
        try:
            llm_out = _summarize_llm(
                previous_summary=conv.conversation_summary or "",
                client_long_memory=client_memory,
                new_turns=[
                    {"role": m.role, "content": m.content} for m in new_turns
                ],
            )
        except Exception:  # noqa: BLE001
            # WARNING : on veut savoir en prod quand le LLM décroche, sans
            # bruit de full stack-trace à chaque fois (déjà loggué au DEBUG
            # niveau httpx). Le fallback heuristique préserve la conv.
            logger.warning(
                "assistance.memory.llm_failed conv=%s — using heuristic fallback",
                conversation_id,
            )
            llm_out = _heuristic_summary_fallback(
                previous_summary=conv.conversation_summary or "",
                new_turns=[
                    {"role": m.role, "content": m.content} for m in new_turns
                ],
            )

        new_summary = (llm_out.get("summary") or "").strip()
        new_facts: list[dict] = list(llm_out.get("facts") or [])
        # Annoter les nouveaux faits avec le numéro de tour (pour traçabilité).
        max_new_turn = max(m.turn_index for m in new_turns)
        for f in new_facts:
            f.setdefault("source_turn", max_new_turn)

        now = datetime.now(timezone.utc)
        # ── 1) écriture conv ──────────────────────────────────────────
        conv.conversation_summary = new_summary or conv.conversation_summary
        conv.conversation_facts = _merge_conv_facts(
            existing=list(conv.conversation_facts or []),
            new=new_facts,
        )
        conv.summarized_until_turn = max_new_turn
        conv.summary_updated_at = now

        # ── 2) écriture client (cross-conv) ───────────────────────────
        if client is not None and new_facts:
            client.assistance_long_memory = _merge_client_long_memory(
                existing=client_memory,
                new_facts=new_facts,
                source_conversation_id=conv.id,
                now=now,
            )

        db.commit()
        # WARNING (pas info) pour visibilité par défaut dans `docker logs` :
        # cet event est l'observabilité principale du module — on veut le
        # voir sans toucher au niveau global du logger uvicorn.
        logger.warning(
            "assistance.memory.consolidated conv=%s up_to_turn=%d facts=+%d client_facts_total=%d",
            conversation_id,
            max_new_turn,
            len(new_facts),
            len((client.assistance_long_memory or {}).get("facts", [])) if client else 0,
        )
    finally:
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass


# ── Appel LLM summarizer ──────────────────────────────────────────────────


_PROMPT_PATH = Path(__file__).parent / "prompts" / "summarizer_system.md"


def _load_system_prompt() -> str:
    """Charge le prompt summarizer une fois (module-level cache)."""
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("summarizer_system.md not found, using minimal fallback prompt")
        return (
            "Tu es un agent de synthèse. Réponds UNIQUEMENT en JSON valide "
            '{"summary": "...", "facts": [], "open_points": []}.'
        )


def _summarize_llm(
    *,
    previous_summary: str,
    client_long_memory: dict,
    new_turns: list[dict],
) -> dict[str, Any]:
    """Appel HTTP OpenAI synchrone, JSON mode strict.

    Lève en cas d'erreur réseau/HTTP/JSON pour que l'appelant retombe sur le
    fallback heuristique.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing")

    system_prompt = _load_system_prompt()
    turns_text = "\n".join(
        f"{t.get('role', '?')}: {t.get('content', '')}" for t in new_turns
    )
    user_payload = (
        f"previous_summary: {previous_summary or '(aucun)'}\n\n"
        f"client_long_memory: {json.dumps(client_long_memory or {}, ensure_ascii=False)}\n\n"
        f"new_turns:\n{turns_text}\n\n"
        "Génère le résumé mis à jour au format JSON strict."
    )

    payload = {
        "model": assistance_summarizer_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        "temperature": assistance_summarizer_temperature(),
        "response_format": {"type": "json_object"},
    }

    r = httpx.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60.0,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"openai_status_{r.status_code}: {r.text[:200]}")

    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("no_choices")
    content = (choices[0].get("message") or {}).get("content") or ""
    parsed = json.loads(content)

    # Sanity check : structure minimale.
    return {
        "summary": parsed.get("summary") or "",
        "facts": _sanitize_facts(parsed.get("facts") or []),
        "open_points": [str(x) for x in (parsed.get("open_points") or [])],
    }


_ALLOWED_FACT_TYPES = {
    "investment_target",
    "investment_horizon",
    "risk_appetite",
    "goal",
    "liquidity_need",
    "monthly_savings",
    "net_worth_bucket",
    "tax_optimization",
    "product_interest",
    "constraint",
    "preference",
    "other",
}


def _sanitize_facts(raw: list) -> list[dict]:
    """Nettoie la liste de faits : type valide, value présent, confidence ∈ [0,1]."""
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = str(item.get("type") or "other")
        if t not in _ALLOWED_FACT_TYPES:
            t = "other"
        v = item.get("value")
        if v is None or v == "":
            continue
        try:
            c = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            c = 0.5
        c = max(0.0, min(1.0, c))
        evidence = str(item.get("evidence") or "")[:200]
        out.append(
            {
                "type": t,
                "value": v,
                "confidence": c,
                "evidence": evidence,
            }
        )
    return out


# ── Fusion / dédup des faits ──────────────────────────────────────────────


def _fact_key(f: dict) -> tuple:
    """Clé de dédup : (type, value normalisée). Permet de fusionner les
    mises à jour (ex. horizon qui change) — voir _merge_conv_facts."""
    return (str(f.get("type") or ""), _normalize_value(f.get("value")))


def _normalize_value(v: Any) -> str:
    if isinstance(v, (int, float)):
        return str(v)
    return str(v).strip().lower() if v is not None else ""


def _merge_conv_facts(*, existing: list[dict], new: list[dict]) -> list[dict]:
    """Merge des faits au niveau de la conv.

    Stratégie :
      - Pour chaque nouveau fact, on regarde s'il existe déjà un fact
        de même `type` dans `existing` :
          - Si oui ET même value → on garde l'existant (évite les doublons
            d'extraction sur les mêmes tours rejoués).
          - Si oui ET value différente → on remplace (ex. horizon mis à
            jour, montant révisé).
          - Si non → on ajoute.
    """
    by_type: dict[str, dict] = {}
    for f in existing:
        t = str(f.get("type") or "")
        if t:
            by_type[t] = f

    for n in new:
        t = str(n.get("type") or "")
        if not t:
            continue
        prev = by_type.get(t)
        if prev is None:
            by_type[t] = n
            continue
        # Même type : on garde la valeur la plus récente sauf si identique
        # (auquel cas on conserve la confidence la plus haute).
        if _normalize_value(prev.get("value")) == _normalize_value(n.get("value")):
            if float(n.get("confidence", 0)) > float(prev.get("confidence", 0)):
                by_type[t] = n
        else:
            by_type[t] = n

    return list(by_type.values())


def _merge_client_long_memory(
    *,
    existing: dict,
    new_facts: list[dict],
    source_conversation_id: UUID,
    now: datetime,
) -> dict:
    """Merge des faits au niveau client (cross-conversations).

    Format stocké :
        {
          "facts": [
            {
              "type": ...,
              "value": ...,
              "confidence": ...,
              "evidence": ...,
              "source_conversation_id": "<uuid>",
              "first_seen_at": "...",
              "last_seen_at": "..."
            }
          ],
          "updated_at": "..."
        }

    Stratégie de dédup :
      - Clé = (type, value normalisée).
      - Si déjà connu : on rafraîchit `last_seen_at` et on garde la
        confidence max (évite l'érosion par des extractions faibles).
      - Si nouveau : on l'ajoute avec `first_seen_at = now`.
      - On ne supprime jamais (la mémoire long-terme est append-mostly).
        Si une valeur change (ex. horizon de 5 → 7 ans), les deux
        coexistent — l'ordre temporel via `last_seen_at` permet à
        l'orchestrateur futur de désambiguïser.
    """
    facts_by_key: dict[tuple, dict] = {}
    for f in (existing.get("facts") or []):
        facts_by_key[_fact_key(f)] = f

    iso_now = now.isoformat()
    for nf in new_facts:
        k = _fact_key(nf)
        if k in facts_by_key:
            prev = facts_by_key[k]
            prev["last_seen_at"] = iso_now
            try:
                prev["confidence"] = max(
                    float(prev.get("confidence", 0)),
                    float(nf.get("confidence", 0)),
                )
            except (TypeError, ValueError):
                pass
            # source_conversation_id : on conserve le premier (origine), on
            # ne réécrit pas — utile pour traçabilité.
        else:
            facts_by_key[k] = {
                **nf,
                "source_conversation_id": str(source_conversation_id),
                "first_seen_at": iso_now,
                "last_seen_at": iso_now,
            }

    return {
        "facts": list(facts_by_key.values()),
        "updated_at": iso_now,
    }


# ── Fallback heuristique ──────────────────────────────────────────────────


def _heuristic_summary_fallback(
    *,
    previous_summary: str,
    new_turns: list[dict],
) -> dict[str, Any]:
    """Fallback ultra-conservateur si le LLM est down.

    On NE crée pas de faits structurés (trop risqué sans NLP) — on se
    contente de marquer dans le summary que de nouveaux échanges ont eu
    lieu, pour ne pas perdre la trace. La consolidation réelle sera
    retentée au tour suivant quand l'API LLM sera de retour.
    """
    n = len(new_turns)
    addendum = f"[Mémoire dégradée] {n} nouvel(s) échange(s) non encore résumé(s)."
    if previous_summary:
        if "[Mémoire dégradée]" in previous_summary:
            summary = previous_summary  # déjà marqué, n'ajoute pas
        else:
            summary = f"{previous_summary} {addendum}"
    else:
        summary = addendum
    return {"summary": summary, "facts": [], "open_points": []}


@dataclass
class MemoryState:
    """Snapshot lisible de l'état mémoire d'une conv (utile pour debug/tests)."""

    conversation_summary: str | None
    conversation_facts: list[dict]
    summarized_until_turn: int | None
    summary_updated_at: datetime | None
    client_long_memory: dict


def load_memory_state(db: Session, conversation_id: UUID) -> MemoryState | None:
    """Charge un snapshot de la mémoire d'une conv.

    Utilisé par `service.build_context` pour assembler le payload du tour
    suivant. Peut retourner None si la conv n'existe pas.
    """
    conv = (
        db.query(AssistanceConversation)
        .filter(AssistanceConversation.id == conversation_id)
        .one_or_none()
    )
    if conv is None:
        return None
    client = (
        db.query(PeClients).filter(PeClients.id == conv.client_id).one_or_none()
    )
    return MemoryState(
        conversation_summary=conv.conversation_summary,
        conversation_facts=list(conv.conversation_facts or []),
        summarized_until_turn=conv.summarized_until_turn,
        summary_updated_at=conv.summary_updated_at,
        client_long_memory=(client.assistance_long_memory if client else {}) or {},
    )
