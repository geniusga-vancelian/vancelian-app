"""Configuration réseaux EVM pour réconciliation / backfill Privy."""
from __future__ import annotations

import os

# Chaînes supportées pour dépôts Privy + réconciliation ledger.
PRIVY_EVM_PILOT_CHAIN_IDS: tuple[int, ...] = (1, 8453)

CHAIN_LABELS: dict[int, str] = {
    1: "Ethereum",
    8453: "Base",
}

# Variables d'environnement RPC par chain_id (première non vide gagne).
_CHAIN_RPC_ENV_KEYS: dict[int, tuple[str, ...]] = {
    1: ("ETHEREUM_RPC_URL", "ETH_RPC_URL", "MAINNET_RPC_URL"),
    8453: ("BASE_RPC_URL", "BASE_RPC_URL_PRIMARY", "NEXT_PUBLIC_BASE_RPC_URL"),
}


def resolve_chain_rpc_url(chain_id: int) -> str | None:
    for key in _CHAIN_RPC_ENV_KEYS.get(chain_id, ()):
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return None


def is_alchemy_rpc(url: str) -> bool:
    return "alchemy.com" in (url or "").lower()


def supported_pilot_chain_ids() -> list[int]:
    return list(PRIVY_EVM_PILOT_CHAIN_IDS)
