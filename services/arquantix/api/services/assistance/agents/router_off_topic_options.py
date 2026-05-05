"""Liste **FIXE** des options renvoyées par le router quand il appelle
``redirect_off_topic`` (Niveau 3 — sujet hors univers Vancelian).

Pourquoi figer ces options :

  * **Cohérence visuelle** : le client voit toujours les mêmes 5 portes
    d'entrée quand il dérape — c'est rassurant et apprend la grammaire
    du bot.
  * **Build de confiance** : le LLM router ne peut plus inventer des
    options bancales (« default → Discuter de Vancelian », etc.).
  * **Audit / debug** : la liste est versionnée git, modifiable par PR
    review, sans migration DB ni cache à invalider.
  * **Consistance avec la roadmap router v2** (cf. user spec
    2026-05-04) : « si hors-sujet complet → recentre le débat sur une
    liste prédéfinie (toujours la même) ».

Le runtime (cf. ``router._parse_redirect_off_topic``) **ignore** les
options fournies par le LLM et substitue cette liste fixe, en y
ajoutant éventuellement un slot dynamique ``resume_topic`` quand la
conversation a un ``current_topic`` non-trivial (cf. lot dedup +
topic v2.8 patch).

──────────────────────────────────────────────────────────────────────
Convention
──────────────────────────────────────────────────────────────────────

  ``OffTopicOption`` = ``{"id": <agent_id>, "label": <client-facing>}``

  ``id`` ∈ {``compliance``, ``advisor``, ``product``, ``market``,
            ``resume_topic``}.

  Note : on peut avoir 2 options pointant vers le même ``agent_id``
  (ex. 2 entrées ``advisor``) si les angles client sont distincts.

──────────────────────────────────────────────────────────────────────
Évolution
──────────────────────────────────────────────────────────────────────

À tenir aligné avec :
  * Le QCM "Welcome / découverte" côté Flutter (si jamais introduit).
  * Le ``redirect_off_topic`` prompt dans ``router_system.md`` qui
    décrit le bridge attendu.

Tests : ``tests/test_assistance_router_off_topic_options_unit.py``.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class OffTopicOption(TypedDict):
    """Une option du QCM renvoyé après ``redirect_off_topic``."""

    id: str
    label: str


# ─────────────────────────────────────────────────────────────────────
# Liste FIXE — version 1 (2026-05-04)
# ─────────────────────────────────────────────────────────────────────
# Ordre choisi pour reflet du parcours client typique :
#   1. compliance — ce qui est le plus opérationnel / urgent (compte)
#   2. product    — la découverte produit, point d'entrée commercial
#   3. advisor    — le conseil personnalisé, valeur ajoutée Vancelian
#   4. market     — la veille marché, expertise complémentaire
#   5. advisor    — second angle advisor (préparer un projet) — distinct du #3

OFF_TOPIC_FIXED_OPTIONS: tuple[OffTopicOption, ...] = (
    {"id": "compliance", "label": "Mon compte et mes opérations"},
    {"id": "product",    "label": "Découvrir un produit Vancelian"},
    {"id": "advisor",    "label": "Conseils pour mes placements"},
    {"id": "market",     "label": "Comprendre les marchés en ce moment"},
    {"id": "advisor",    "label": "Préparer un projet financier"},
)

OFF_TOPIC_RESUME_OPTION_ID = "resume_topic"


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _format_topic_label(topic: dict[str, Any]) -> Optional[str]:
    """Construit un label client-friendly pour ``resume_topic`` à partir
    du ``current_topic`` persisté dans ``assistance_conversations``.

    Format préféré (par ordre de priorité) :
      1. ``topic["display_label"]`` si fourni (champ libre éditorial).
      2. ``"<product_code>"`` (ex. *« TOP_5 »*) — court et précis.
      3. ``"<kind>"`` (ex. *« vancelian_product »*) — fallback technique.
      4. ``None`` → on n'ajoute pas le slot resume.

    On reste défensif : on ne fait pas confiance aux types côté DB et
    on tronque tout label à 80 chars.
    """
    if not isinstance(topic, dict):
        return None
    display = topic.get("display_label")
    if isinstance(display, str) and display.strip():
        return display.strip()[:80]
    product_code = topic.get("product_code")
    if isinstance(product_code, str) and product_code.strip():
        return product_code.strip()[:80]
    kind = topic.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()[:80]
    return None


def build_off_topic_options(
    *,
    current_topic: Optional[dict[str, Any]] = None,
) -> list[OffTopicOption]:
    """Retourne la liste finale d'options pour ``redirect_off_topic``,
    avec optionnellement le slot dynamique ``resume_topic`` en 1ʳᵉ
    position si la conversation a un sujet engagé.

    Le slot ``resume_topic`` est résolu côté ``service._decide_agent``
    en remontant l'agent_used du dernier turn assistant non-router.
    """
    options: list[OffTopicOption] = []

    resume_label = _format_topic_label(current_topic) if current_topic else None
    if resume_label:
        options.append(
            {
                "id": OFF_TOPIC_RESUME_OPTION_ID,
                "label": f"Reprendre {resume_label}",
            }
        )

    for opt in OFF_TOPIC_FIXED_OPTIONS:
        options.append({"id": opt["id"], "label": opt["label"]})

    return options


__all__ = [
    "OffTopicOption",
    "OFF_TOPIC_FIXED_OPTIONS",
    "OFF_TOPIC_RESUME_OPTION_ID",
    "build_off_topic_options",
]
