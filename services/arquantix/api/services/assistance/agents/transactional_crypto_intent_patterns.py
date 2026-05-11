"""Motifs transactionnels crypto — source unique pour la garde avant LLM.

P0.5 : comportement déterministe sur les verbes « acquisition » (spot) vs swap.

Les verbes ``convertir|swap|échanger`` ne sont **pas** dans ``spot_acquisition`` :
ils alimentent la branche dédiée ``crypto_swap``, évaluée **après** l’achat /
intent spot dans ``router.py`` pour limiter les conflits de classification.

Référence agrégée : dict immuable ``TRANSACTIONAL_CRYPTO_INTENT_PATTERNS``.
"""

from __future__ import annotations

import re
from re import Pattern
from types import MappingProxyType
from typing import Final, Mapping

RE_SPOT_CRYPTO_ACQUISITION_VERB: Final[Pattern[str]] = re.compile(
    r"\b(?:"
    r"acheter\b|achetons\b|achète\b|achetez\b"
    r"|investir\b|investis\b|investissons\b|investissez\b|investissant\b"
    r"|réinvestir\b|réinvestis\b"
    r"|renforc(?:er|es|ez|ons|e)\b"
    r"|placer\b|plaçons\b|placez\b"
    r"|buy(?:ing)?\b|purchase\b|purchasing\b"
    # « mettre tout / mets tout … » évite les faux positifs (« mettre en place » sans actif crypto).
    r"|(?:mettre|mets)\s+tout\b"
    r"|augmenter\s+(?:ma|mon|ta|sa|leur|notre)\s+position\b"
    r"|renforcer\s+(?:ma|mon|ta|sa|leur|notre)\s+position\b"
    r")\b",
    re.I,
)

RE_SPOT_CRYPTO_SWAP_VERB: Final[Pattern[str]] = re.compile(
    r"\b(?:échanger|echanger|swap|swapper|convertir)\b",
    re.I,
)

TRANSACTIONAL_CRYPTO_INTENT_PATTERNS: Final[Mapping[str, Pattern[str]]] = MappingProxyType(
    {
        "spot_acquisition": RE_SPOT_CRYPTO_ACQUISITION_VERB,
        "spot_swap": RE_SPOT_CRYPTO_SWAP_VERB,
    },
)


def matches_spot_acquisition_verb(text: str) -> bool:
    """Intention formulée comme acquisition / placement spot (≠ swap)."""
    raw = (text or "").strip()
    if not raw:
        return False
    return RE_SPOT_CRYPTO_ACQUISITION_VERB.search(raw.lower().replace("’", "'")) is not None


def matches_spot_swap_verb(text: str) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    return RE_SPOT_CRYPTO_SWAP_VERB.search(raw.lower().replace("’", "'")) is not None


__all__ = [
    "TRANSACTIONAL_CRYPTO_INTENT_PATTERNS",
    "RE_SPOT_CRYPTO_ACQUISITION_VERB",
    "RE_SPOT_CRYPTO_SWAP_VERB",
    "matches_spot_acquisition_verb",
    "matches_spot_swap_verb",
]
