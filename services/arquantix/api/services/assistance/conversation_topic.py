"""Phase 2 wiki v1.4 patch — slot mémoire « topic en cours » par conversation.

Module **pur** (pas de dépendance LLM, pas d'OpenAI) qui matérialise le
sujet actif d'une conversation. Lu par le router pour stabiliser les
follow-ups, et écrit automatiquement par le runtime après chaque tool
call expert qui ancre un sujet.

──────────────────────────────────────────────────────────────────────
Modèle

`Topic` est un dict-like (JSONB) avec ce schéma logique :

    {
      "kind": "vancelian_product" | "instrument" | "topic_other",
      "product_code": str | None,        # si kind=vancelian_product
      "instrument_symbol": str | None,   # si kind=instrument
      "agent_owner": str,                # agent_id qui a posé le sujet
      "set_at_turn": int,                # turn_index global au moment du set
      "set_by_tool": str,                # nom du tool qui a déclenché
      "confidence": float,               # 0..1
      "set_at": str,                     # ISO-8601 UTC
    }

──────────────────────────────────────────────────────────────────────
Cycle de vie

  1. Au démarrage d'une conversation : `current_topic = NULL`.
  2. Quand un tool « ancrant » réussit (cf. `TOPIC_ANCHORING_TOOLS`),
     le runtime appelle `infer_topic_from_tool_call(...)` qui retourne
     un Topic prêt à persister, puis `set_topic(...)` qui écrit en DB.
  3. Le router lit `get_topic(...)` au début de chaque tour et l'injecte
     dans son prompt user.
  4. Sur un `redirect_off_topic` (router) ou un changement explicite,
     le runtime appelle `clear_topic(...)`.
  5. Pas d'expiration temporelle automatique : le sujet vit tant
     qu'aucun nouveau ne l'écrase. C'est intentionnel — un follow-up
     5 minutes plus tard est aussi légitime qu'1 seconde plus tard.

──────────────────────────────────────────────────────────────────────
Tests : `tests/test_assistance_conversation_topic_unit.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AssistanceConversation


# ─────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────


# Tools dont l'appel **ancre** un sujet sur la conversation. Mapping
# `tool_name -> kind`. Liste extensible — ne pas ajouter un tool sans
# valider qu'il **identifie nominativement** un sujet (un tool qui
# retourne une LISTE n'ancre rien : c'est une exploration).
TOPIC_ANCHORING_TOOLS: dict[str, str] = {
    # Vrais ancreurs : un seul produit / instrument visé.
    "show_bundle_detail": "vancelian_product",
    "show_instrument_card": "instrument",
    # `read_wiki_page` : ancre le sujet sur la fiche lue (catégorie +
    # slug). On reste sur kind=topic_other car ce n'est pas forcément
    # un produit Vancelian (peut être une fiche FAQ, account, etc.).
    "read_wiki_page": "topic_other",
    # `read_product_knowledge` : SQL fiches courtes — peut ancrer si la
    # fiche est descriptive d'un produit (sinon c'est une définition
    # générique). On délègue le filtrage à `infer_topic_from_tool_call`.
    "read_product_knowledge": "topic_other",
}


# Confiance par défaut quand on infère le topic depuis le tool call.
# Volontairement haut (0.95) — on est dans le cas où l'agent a appelé
# un tool **qualifié** qui identifie un sujet précis.
DEFAULT_TOPIC_CONFIDENCE: float = 0.95


# ─────────────────────────────────────────────────────────────────────
# Persistance — getters / setters
# ─────────────────────────────────────────────────────────────────────


def get_topic(db: Session, conversation_id: UUID | str) -> Optional[dict[str, Any]]:
    """Lit le slot `current_topic` d'une conversation.

    Retourne `None` si :
      * la conv n'existe pas (cas pathologique),
      * le slot est NULL (pas encore set),
      * le slot a un format invalide (defensive — pas d'exception remontée).
    """
    conv = (
        db.query(AssistanceConversation)
        .filter(AssistanceConversation.id == conversation_id)
        .one_or_none()
    )
    if conv is None:
        return None
    topic = conv.current_topic
    if not isinstance(topic, dict):
        return None
    return dict(topic)


def set_topic(
    db: Session,
    conversation_id: UUID | str,
    topic: dict[str, Any],
    *,
    commit: bool = True,
) -> None:
    """Écrit le slot `current_topic`. Idempotent (pas d'historique des
    sujets précédents — on ne garde que le sujet actif).

    Le caller est responsable du formatage : utiliser
    `infer_topic_from_tool_call(...)` côté runtime pour ne pas dupliquer
    la logique de formatage.
    """
    conv = (
        db.query(AssistanceConversation)
        .filter(AssistanceConversation.id == conversation_id)
        .one_or_none()
    )
    if conv is None:
        return
    conv.current_topic = topic
    if commit:
        db.commit()


def clear_topic(
    db: Session,
    conversation_id: UUID | str,
    *,
    commit: bool = True,
) -> None:
    """Réinitialise le slot (NULL). À appeler sur `redirect_off_topic`
    ou changement de sujet explicite détecté par le router."""
    conv = (
        db.query(AssistanceConversation)
        .filter(AssistanceConversation.id == conversation_id)
        .one_or_none()
    )
    if conv is None:
        return
    conv.current_topic = None
    if commit:
        db.commit()


# ─────────────────────────────────────────────────────────────────────
# Inférence depuis un tool call
# ─────────────────────────────────────────────────────────────────────


def infer_topic_from_tool_call(
    *,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_result: dict[str, Any],
    agent_id: str,
    turn_index: int,
) -> Optional[dict[str, Any]]:
    """Construit un Topic à partir d'un tool call qualifié, ou retourne
    `None` si le tool n'est pas ancrant ou si les données sont insuffisantes.

    Cette fonction est **pure** — pas de DB, pas de LLM. Le caller
    (runtime `agent_loop`) décide ensuite de persister ou non.
    """
    if tool_name not in TOPIC_ANCHORING_TOOLS:
        return None
    if not isinstance(tool_result, dict):
        return None

    kind = TOPIC_ANCHORING_TOOLS[tool_name]
    base = {
        "kind": kind,
        "agent_owner": agent_id,
        "set_at_turn": int(turn_index),
        "set_by_tool": tool_name,
        "confidence": DEFAULT_TOPIC_CONFIDENCE,
        "set_at": datetime.now(timezone.utc).isoformat(),
    }

    if tool_name == "show_bundle_detail":
        # Le tool retourne `bundle.product_code` quand il a réussi à
        # matcher un bundle. On ne set le topic que sur succès — sinon
        # on a un `error` dans `tool_result`.
        bundle = tool_result.get("bundle") or {}
        product_code = (bundle.get("product_code") or "").strip()
        if not product_code:
            return None
        return {**base, "product_code": product_code.upper()}

    if tool_name == "show_instrument_card":
        symbol = (
            tool_result.get("symbol")
            or tool_result.get("instrument_symbol")
            or ""
        )
        symbol = str(symbol).strip().upper()
        if not symbol:
            return None
        return {**base, "instrument_symbol": symbol}

    if tool_name == "read_wiki_page":
        category = str(tool_result.get("category") or "").strip()
        slug = str(tool_result.get("slug") or "").strip()
        if not category or not slug:
            return None
        return {**base, "wiki_category": category, "wiki_slug": slug}

    if tool_name == "read_product_knowledge":
        slug = str(tool_result.get("slug") or "").strip()
        if not slug:
            return None
        return {**base, "knowledge_slug": slug}

    return None


# ─────────────────────────────────────────────────────────────────────
# Sérialisation côté router
# ─────────────────────────────────────────────────────────────────────


def render_topic_for_prompt(topic: Optional[dict[str, Any]]) -> str:
    """Rend un Topic en libellé court à injecter dans le prompt user du
    router. Volontairement compact (1-2 lignes) pour ne pas gonfler le
    contexte.

    Retourne `""` si `topic` est None ou mal formé — le router ignorera
    silencieusement (pas de section vide dans le prompt).
    """
    if not isinstance(topic, dict):
        return ""

    kind = str(topic.get("kind") or "").strip()
    owner = str(topic.get("agent_owner") or "").strip()
    if not kind or not owner:
        return ""

    if kind == "vancelian_product":
        code = str(topic.get("product_code") or "").strip()
        if not code:
            return ""
        return (
            f"Sujet en cours : produit Vancelian `{code}` "
            f"(agent owner: {owner})."
        )
    if kind == "instrument":
        sym = str(topic.get("instrument_symbol") or "").strip()
        if not sym:
            return ""
        return (
            f"Sujet en cours : instrument coté {sym} "
            f"(agent owner: {owner})."
        )
    if kind == "topic_other":
        ws = str(topic.get("wiki_slug") or "").strip()
        ks = str(topic.get("knowledge_slug") or "").strip()
        label = ws or ks or "fiche connaissance"
        return f"Sujet en cours : {label} (agent owner: {owner})."

    return ""


__all__ = [
    "TOPIC_ANCHORING_TOOLS",
    "DEFAULT_TOPIC_CONFIDENCE",
    "get_topic",
    "set_topic",
    "clear_topic",
    "infer_topic_from_tool_call",
    "render_topic_for_prompt",
]
