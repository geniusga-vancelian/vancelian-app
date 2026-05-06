"""Helpers read-only pour lire le ``current_topic`` depuis ``ToolContext``.

Cognitive Bot v4 — Lot 4 « Topic mémoire cross-tour » (2026-05-06).

Ce module offre une API stable et défensive pour les tools qui veulent
adapter leur comportement au sujet actif de la conversation, sans avoir
à réimplémenter le décodage du dict ``current_topic`` (cf.
``services.assistance.conversation_topic`` pour la source de vérité).

──────────────────────────────────────────────────────────────────────
Pourquoi des helpers et pas un accès direct ?
──────────────────────────────────────────────────────────────────────

* ``ctx.current_topic`` est un ``Optional[dict]``. Schéma multi-kind
  (vancelian_product / instrument / topic_other) avec champs
  conditionnels (``product_code`` vs ``instrument_symbol`` vs
  ``wiki_slug`` / ``knowledge_slug``). Sans helper, chaque tool
  réinvente la roue avec un risque d'incohérence.
* On veut que les tools restent **agnostiques** du format DB exact
  (si on étend le schéma, on n'a qu'un seul point de mise à jour ici
  + ``conversation_topic.py``).
* On veut une **batterie de helpers testable** (cf.
  ``tests/test_assistance_topic_context_unit.py``).

──────────────────────────────────────────────────────────────────────
Convention de fallback
──────────────────────────────────────────────────────────────────────

Quand le topic n'est pas disponible (``None``, dict vide, kind inconnu),
tous les helpers renvoient ``None`` ou ``False`` (pas de topic = pas
de contrainte). C'est cohérent avec le cycle de vie côté
``conversation_topic.py`` (au tour 0, ``current_topic = NULL``).

──────────────────────────────────────────────────────────────────────
Sécurité & invariants
──────────────────────────────────────────────────────────────────────

* **Read-only** : aucun helper ne mute ``ctx.current_topic`` ni la DB.
* **Pure** : pas d'I/O, pas de DB, pas de LLM.
* **Pas d'exception** : une entrée mal formée renvoie le défaut.
* **Pas de cycle d'import** : ``ToolContext`` importé via
  ``TYPE_CHECKING`` uniquement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from services.assistance.agents.tools.contracts import ToolContext


# ─────────────────────────────────────────────────────────────────────
# Constantes — alignées sur conversation_topic.py
# ─────────────────────────────────────────────────────────────────────


# Kinds connus. Recopiés ici (vs import) pour éviter le cycle ; un test
# garantit la cohérence avec ``conversation_topic.TOPIC_ANCHORING_TOOLS``.
KNOWN_TOPIC_KINDS: frozenset[str] = frozenset({
    "vancelian_product",
    "instrument",
    "topic_other",
})


# ─────────────────────────────────────────────────────────────────────
# Lecture défensive
# ─────────────────────────────────────────────────────────────────────


def has_current_topic(ctx: "ToolContext") -> bool:
    """``True`` si un topic actif et bien formé est posé."""
    return get_current_topic_kind(ctx) is not None


def get_current_topic_kind(ctx: "ToolContext") -> Optional[str]:
    """Retourne le ``kind`` du topic actif ou ``None``.

    Garanti d'être dans ``KNOWN_TOPIC_KINDS`` quand non-``None``.
    """
    topic = ctx.current_topic
    if not isinstance(topic, dict):
        return None
    raw = topic.get("kind")
    if not isinstance(raw, str):
        return None
    val = raw.strip().lower()
    return val if val in KNOWN_TOPIC_KINDS else None


def get_current_topic_product_code(ctx: "ToolContext") -> Optional[str]:
    """Retourne le ``product_code`` (ex. ``"TOP5"``) si le topic est un
    ``vancelian_product``, sinon ``None``.

    Renvoie systématiquement la valeur en MAJUSCULES (alignement avec
    ``infer_topic_from_tool_call`` côté ``show_bundle_detail``).
    """
    if get_current_topic_kind(ctx) != "vancelian_product":
        return None
    raw = ctx.current_topic.get("product_code") if ctx.current_topic else None
    if not isinstance(raw, str):
        return None
    val = raw.strip().upper()
    return val or None


def get_current_topic_instrument_symbol(ctx: "ToolContext") -> Optional[str]:
    """Retourne le ``instrument_symbol`` (ex. ``"BTC"``) si le topic est
    un ``instrument``, sinon ``None``.

    Renvoie systématiquement la valeur en MAJUSCULES.
    """
    if get_current_topic_kind(ctx) != "instrument":
        return None
    raw = (
        ctx.current_topic.get("instrument_symbol") if ctx.current_topic else None
    )
    if not isinstance(raw, str):
        return None
    val = raw.strip().upper()
    return val or None


def get_current_topic_agent_owner(ctx: "ToolContext") -> Optional[str]:
    """Retourne l'``agent_id`` qui a posé le sujet (utile pour audit /
    routing). ``None`` si absent."""
    topic = ctx.current_topic
    if not isinstance(topic, dict):
        return None
    raw = topic.get("agent_owner")
    if not isinstance(raw, str):
        return None
    val = raw.strip()
    return val or None


def get_current_topic_label(ctx: "ToolContext") -> Optional[str]:
    """Retourne un libellé court et stable du sujet actif, indépendant
    du ``kind`` — utilisable dans un message texte du LLM ou un log.

    Exemples :
      * vancelian_product TOP5 → ``"vancelian_product:TOP5"``
      * instrument BTC        → ``"instrument:BTC"``
      * topic_other wiki     → ``"topic_other:<slug>"``

    ``None`` si aucun topic actif.
    """
    kind = get_current_topic_kind(ctx)
    if kind is None:
        return None
    if kind == "vancelian_product":
        code = get_current_topic_product_code(ctx)
        return f"vancelian_product:{code}" if code else None
    if kind == "instrument":
        sym = get_current_topic_instrument_symbol(ctx)
        return f"instrument:{sym}" if sym else None
    if kind == "topic_other":
        topic = ctx.current_topic or {}
        ws = str(topic.get("wiki_slug") or "").strip()
        ks = str(topic.get("knowledge_slug") or "").strip()
        slug = ws or ks
        return f"topic_other:{slug}" if slug else "topic_other"
    return None


def topic_matches_product_code(
    ctx: "ToolContext", product_code: Optional[str]
) -> bool:
    """``True`` si le topic actif est ``vancelian_product`` ET que
    ``product_code`` correspond (case-insensitive).

    Utile pour : un tool ``show_bundle_detail`` peut détecter qu'un
    LLM tente de basculer vers un autre bundle alors que le sujet
    actif est différent (anti-dérive).
    """
    target = (product_code or "").strip().upper()
    if not target:
        return False
    return get_current_topic_product_code(ctx) == target


def topic_matches_instrument_symbol(
    ctx: "ToolContext", symbol: Optional[str]
) -> bool:
    """``True`` si le topic actif est ``instrument`` ET que ``symbol``
    correspond (case-insensitive).

    Utile pour : ``show_instrument_card`` peut détecter qu'un LLM
    invoque ``BTC`` alors que le sujet actif est ``ETH``.
    """
    target = (symbol or "").strip().upper()
    if not target:
        return False
    return get_current_topic_instrument_symbol(ctx) == target


def topic_snapshot(ctx: "ToolContext") -> dict[str, Any]:
    """Snapshot compact, lisible et JSON-safe du topic — pour log /
    audit / hint dans un payload d'erreur de tool.

    Structure stable :
      {
        "has_topic": bool,
        "kind": str | None,
        "label": str | None,
        "agent_owner": str | None,
      }
    """
    return {
        "has_topic": has_current_topic(ctx),
        "kind": get_current_topic_kind(ctx),
        "label": get_current_topic_label(ctx),
        "agent_owner": get_current_topic_agent_owner(ctx),
    }


__all__ = [
    "KNOWN_TOPIC_KINDS",
    "has_current_topic",
    "get_current_topic_kind",
    "get_current_topic_product_code",
    "get_current_topic_instrument_symbol",
    "get_current_topic_agent_owner",
    "get_current_topic_label",
    "topic_matches_product_code",
    "topic_matches_instrument_symbol",
    "topic_snapshot",
]
