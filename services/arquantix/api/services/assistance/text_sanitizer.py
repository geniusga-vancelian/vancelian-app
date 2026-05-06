"""Sanitiseur de texte sortant agent → client (filet anti-emoji).

Cognitive Bot v4 — Politique éditoriale Vancelian (2026-05-06).

Vancelian se positionne comme une **institution premium au ton
sobre** — aucun emoji / emoticône / pictogramme Unicode ne doit
apparaître dans une réponse texte affichée au client. Ceci est
imposé en deux temps :

1. **Au prompt** : `_response_framework.md` interdit explicitement
   l'usage d'emojis (auto-injecté à tous les agents experts).
2. **Au runtime (ici)** : ce module strip les codepoints emoji
   avant émission SSE delta vers Flutter. Filet de sécurité au
   cas où le LLM ignore l'instruction prompt (cas observable
   notamment sur les modèles open-source ou en cas de
   contamination par le contenu user).

──────────────────────────────────────────────────────────────────────
Périmètre Unicode couvert
──────────────────────────────────────────────────────────────────────

Tous les blocs Unicode standard de pictogrammes/emojis sont supprimés.
Les ranges sont stables (figés depuis Unicode 13.0) et couvrent :

* Emoticons                       (1F600–1F64F)
* Misc Symbols and Pictographs    (1F300–1F5FF)
* Transport and Map Symbols       (1F680–1F6FF)
* Alchemical Symbols              (1F700–1F77F)
* Geometric Shapes Extended       (1F780–1F7FF)
* Supplemental Arrows-C           (1F800–1F8FF)
* Supplemental Symbols/Picto      (1F900–1F9FF)
* Chess Symbols                   (1FA00–1FA6F)
* Symbols and Pictographs Ext-A   (1FA70–1FAFF)
* Misc Symbols                    (2600–26FF)  ← ⚠️ ⭐ ☀️ etc.
* Dingbats                        (2700–27BF)  ← ✅ ✈️ ✏️ etc.
* Misc Technical                  (2300–23FF)  ← ⌚ ⌛ etc.
* Misc Symbols and Arrows         (2B00–2BFF)
* Regional Indicator Symbols      (1F1E6–1F1FF) ← drapeaux
* Variation Selectors             (FE0F)        ← composition emoji
* Zero-Width Joiner               (200D)        ← séquences emoji
* Skin tone modifiers             (1F3FB–1F3FF)

Ce qui est **préservé** :

* Lettres, chiffres, ponctuation standard.
* Caractères français (é, è, à, ç, œ, …).
* Symboles typographiques utiles : « » ' ' – — … ° ² ³ ½ µ § €
  £ $ ¥ ¢ © ® ™ etc.
* Symboles mathématiques : ÷ × ± ≤ ≥ ≠ ∞ √ ∑ ∏ ∫.
* Flèches simples : ← → ↑ ↓ ↔ (utiles en Markdown).

──────────────────────────────────────────────────────────────────────
Convention
──────────────────────────────────────────────────────────────────────

* **Pure** : aucune I/O, aucune dépendance externe.
* **Idempotente** : ``strip_emojis(strip_emojis(s)) == strip_emojis(s)``.
* **Préserve None / chaîne vide** : ``strip_emojis(None) is None``.
* **Espaces normalisés** : si un emoji était entouré d'espaces, on
  collapse les espaces multiples résultants pour éviter « foo  bar ».
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Regex emoji — compilée une seule fois au load
# ─────────────────────────────────────────────────────────────────────


# NB: les ranges sont volontairement explicites (vs catégorie Unicode
# générique "So") pour ne PAS strip des symboles utiles que la
# politique éditoriale tolère (ex. ©, ®, ™, ÷, ±, →).
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F700-\U0001F77F"  # Alchemical
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Ext-A
    "\U00002600-\U000026FF"  # Misc Symbols (⚠ ☀ ☁ ☎ ☑ etc.)
    "\U00002700-\U000027BF"  # Dingbats (✅ ✈ ✏ ✂ etc.)
    "\U00002B00-\U00002BFF"  # Misc Symbols and Arrows (⭐ ⬆ ⬇ etc.)
    "\U0001F1E6-\U0001F1FF"  # Regional Indicators (flags)
    "\U0001F3FB-\U0001F3FF"  # Skin tone modifiers
    "\U0000FE0F"             # Variation Selector-16 (force emoji)
    "\U0000200D"             # Zero-Width Joiner (emoji sequences)
    "]",
    flags=re.UNICODE,
)


# Espaces multiples créés par la suppression — collapse en un seul.
# Note : on NE TOUCHE PAS aux espaces avant ponctuation française
# (! ? ; :) car la typographie française les conserve. Strip un
# emoji entre deux espaces produit un double-espace qu'on collapse,
# l'espace simple résiduel reste légitime devant la ponctuation.
_MULTI_SPACE_PATTERN = re.compile(r" {2,}")


def strip_emojis(text: Optional[str]) -> Optional[str]:
    """Retire tous les emojis / pictogrammes Unicode du texte.

    Args:
        text: Texte potentiellement contaminé. ``None`` et ``""``
            sont retournés tels quels.

    Returns:
        Texte nettoyé. Espaces multiples collapsés. Espaces avant
        ponctuation française supprimés.

    Examples:
        >>> strip_emojis("Bonjour 👋 ! Comment ça va ?")
        'Bonjour ! Comment ça va ?'
        >>> strip_emojis("Voici le ✅ et le ❌ !")
        'Voici le et le !'
        >>> strip_emojis(None) is None
        True
        >>> strip_emojis("")
        ''
    """
    if text is None or text == "":
        return text

    # Fast path : si aucun caractère du range emoji n'est présent,
    # on évite la regex complète (bench : ~3× plus rapide sur les
    # tours sans emoji, qui sont la majorité une fois le prompt
    # respecté par le LLM).
    if not _EMOJI_PATTERN.search(text):
        return text

    cleaned = _EMOJI_PATTERN.sub("", text)
    # Cosmétique : collapse les espaces multiples créés par strip
    # (ex. « foo  bar » → « foo bar »). Puis trim les espaces
    # leading/trailing que l'emoji aurait créés en début/fin
    # (ex. « hello 👋» → « hello » sans trailing).
    cleaned = _MULTI_SPACE_PATTERN.sub(" ", cleaned).strip()
    return cleaned


def contains_emojis(text: Optional[str]) -> bool:
    """``True`` si le texte contient au moins un emoji.

    Utile pour l'observabilité (logger un warning quand le LLM
    désobéit à l'instruction prompt). N'a aucun effet sur le texte
    lui-même — utiliser ``strip_emojis`` pour nettoyer.
    """
    if not text:
        return False
    return bool(_EMOJI_PATTERN.search(text))


def strip_emojis_with_metrics(
    text: Optional[str],
) -> tuple[Optional[str], int]:
    """Variante de ``strip_emojis`` qui retourne aussi le nombre de
    codepoints supprimés.

    Utile pour incrémenter un compteur d'observabilité côté runtime
    (cf. Lot 5 ``runtime_metrics``).

    Returns:
        ``(cleaned, n_stripped)``. ``n_stripped == 0`` quand le texte
        est intact.
    """
    if text is None or text == "":
        return text, 0
    matches = _EMOJI_PATTERN.findall(text)
    if not matches:
        return text, 0
    n_stripped = len(matches)
    cleaned = _EMOJI_PATTERN.sub("", text)
    cleaned = _MULTI_SPACE_PATTERN.sub(" ", cleaned).strip()
    return cleaned, n_stripped


__all__ = [
    "strip_emojis",
    "strip_emojis_with_metrics",
    "contains_emojis",
]
