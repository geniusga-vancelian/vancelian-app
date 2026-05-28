"""Résolution chain label → chain_id (pilote Base)."""
from __future__ import annotations

CHAIN_BASE = 8453

_CHAIN_ALIASES: dict[str, int] = {
    "base": CHAIN_BASE,
    "8453": CHAIN_BASE,
    "eip155:8453": CHAIN_BASE,
}


def resolve_chain_id(chain: str) -> int:
    key = (chain or "").strip().lower()
    if key not in _CHAIN_ALIASES:
        raise ValueError(f"Chaîne non supportée pour l'indexer : {chain!r} (pilote : base)")
    return _CHAIN_ALIASES[key]


def chain_label(chain_id: int) -> str:
    if chain_id == CHAIN_BASE:
        return "base"
    return str(chain_id)
