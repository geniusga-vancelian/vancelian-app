"""Configuration réseaux EVM pour réconciliation / backfill Privy."""
from __future__ import annotations

import os
import re

# Chaînes supportées pour dépôts Privy + réconciliation ledger (Base toujours ; ETH si RPC dispo).
PRIVY_EVM_PILOT_CHAIN_IDS: tuple[int, ...] = (8453, 1)

CHAIN_LABELS: dict[int, str] = {
    1: "Ethereum",
    8453: "Base",
}

# Variables d'environnement RPC par chain_id (première non vide gagne).
_CHAIN_RPC_ENV_KEYS: dict[int, tuple[str, ...]] = {
    1: ("ETHEREUM_RPC_URL", "ETH_RPC_URL", "MAINNET_RPC_URL"),
    8453: ("BASE_RPC_URL", "BASE_RPC_URL_PRIMARY", "NEXT_PUBLIC_BASE_RPC_URL"),
}


def _derive_ethereum_rpc_from_base_alchemy() -> str | None:
    """Dérive eth-mainnet Alchemy depuis BASE_RPC_URL quand ETHEREUM_RPC_URL est absent."""
    base = (os.getenv("BASE_RPC_URL") or os.getenv("BASE_RPC_URL_PRIMARY") or "").strip()
    match = re.search(r"g\.alchemy\.com/v2/([^/?]+)", base)
    if not match:
        return None
    return f"https://eth-mainnet.g.alchemy.com/v2/{match.group(1)}"


def resolve_chain_rpc_url(chain_id: int) -> str | None:
    for key in _CHAIN_RPC_ENV_KEYS.get(chain_id, ()):
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    if chain_id == 1:
        return _derive_ethereum_rpc_from_base_alchemy()
    return None


def is_alchemy_rpc(url: str) -> bool:
    return "alchemy.com" in (url or "").lower()


def supported_pilot_chain_ids() -> list[int]:
    return [cid for cid in PRIVY_EVM_PILOT_CHAIN_IDS if resolve_chain_rpc_url(cid)]
