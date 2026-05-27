"""Whitelist stricte des actifs et chaînes autorisés pour les swaps LI.FI V1.

Routing 100 % Base (chain 8453) — source de vérité : ``base_allowed_assets``.
Aucune adresse de contrat côté front.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Union

from config.base_allowed_assets import (
    BASE_ALLOWED_ASSETS,
    BASE_CHAIN_KEY,
    BASE_LIFI_CHAIN_ID,
    BASE_SWAP_SYMBOLS,
    EVM_NATIVE_TOKEN,
)
from services.lifi.config import swap_v1_pilot_chains

SWAP_V1_EVM_CHAIN_KEYS: frozenset[str] = frozenset({BASE_CHAIN_KEY})
SWAP_V1_SOURCE_ASSETS: frozenset[str] = BASE_SWAP_SYMBOLS
SWAP_V1_DESTINATION_ASSETS: frozenset[str] = BASE_SWAP_SYMBOLS

SUPPORTED_SWAP_CHAINS: dict[str, dict[str, Any]] = {
    BASE_CHAIN_KEY: {
        "lifi_chain_id": BASE_LIFI_CHAIN_ID,
        "display_name": "Base",
        "wallet_chain_type": "ethereum",
        "evm": True,
    },
}

DEFAULT_MIN_SWAP_AMOUNT: dict[str, Decimal] = {
    "ETH": Decimal("0.001"),
    "USDC": Decimal("5"),
    "EURC": Decimal("5"),
    "CBBTC": Decimal("0.00001"),
    "LINK": Decimal("1"),
    "AAVE": Decimal("0.01"),
    "UNI": Decimal("0.1"),
}

DEFAULT_MAX_SWAP_AMOUNT: dict[str, Decimal] = {
    "ETH": Decimal("50"),
    "USDC": Decimal("250000"),
    "EURC": Decimal("250000"),
    "CBBTC": Decimal("5"),
    "LINK": Decimal("50000"),
    "AAVE": Decimal("50000"),
    "UNI": Decimal("50000"),
}


def _build_supported_swap_assets() -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for row in BASE_ALLOWED_ASSETS:
        if not row["swap_enabled"] or not row["base_token_address"]:
            continue
        sym = row["symbol"]
        assets[sym] = {
            "display_name": row["name"],
            "symbol": sym,
            "decimals": row["decimals"],
            "kind": row["kind"],
            "chains": [BASE_CHAIN_KEY],
            "addresses": {BASE_CHAIN_KEY: row["base_token_address"]},
        }
    return assets


SUPPORTED_SWAP_ASSETS: dict[str, dict[str, Any]] = _build_supported_swap_assets()


@dataclass(frozen=True)
class ResolvedSwapToken:
    asset: str
    chain_key: str
    lifi_chain_id: Union[int, str]
    token_address: str
    decimals: int
    display_name: str


def normalize_chain_key(chain: str) -> str:
    key = (chain or "").strip().lower()
    aliases = {
        "eth": "ethereum",
        "mainnet": "ethereum",
        "arb": "arbitrum",
        "matic": "polygon",
        "pol": "polygon",
    }
    normalized = aliases.get(key, key)
    if normalized == "ethereum":
        return BASE_CHAIN_KEY
    return normalized


def normalize_asset_symbol(asset: str) -> str:
    raw = (asset or "").strip().upper()
    if raw in {"CBTC", "CBBTC", "WBTC"}:
        return "CBBTC"
    return raw


def is_evm_swap_chain(chain_key: str) -> bool:
    return normalize_chain_key(chain_key) in SWAP_V1_EVM_CHAIN_KEYS


def is_supported_chain(chain_key: str) -> bool:
    chain = normalize_chain_key(chain_key)
    return chain in SUPPORTED_SWAP_CHAINS and is_evm_swap_chain(chain)


def is_supported_asset(asset: str) -> bool:
    return normalize_asset_symbol(asset) in SUPPORTED_SWAP_ASSETS


def is_swap_source_asset(asset: str) -> bool:
    return normalize_asset_symbol(asset) in SWAP_V1_SOURCE_ASSETS


def is_swap_destination_asset(asset: str) -> bool:
    return normalize_asset_symbol(asset) in SWAP_V1_DESTINATION_ASSETS


def asset_available_on_chain(asset: str, chain_key: str) -> bool:
    sym = normalize_asset_symbol(asset)
    chain = normalize_chain_key(chain_key)
    meta = SUPPORTED_SWAP_ASSETS.get(sym)
    if not meta:
        return False
    if not is_evm_swap_chain(chain):
        return False
    return chain in meta.get("chains", [])


def resolve_swap_token(asset: str, chain_key: str) -> ResolvedSwapToken:
    sym = normalize_asset_symbol(asset)
    chain = normalize_chain_key(chain_key)
    if sym not in SUPPORTED_SWAP_ASSETS:
        raise ValueError(f"Asset non whitelisté: {sym}")
    if chain not in SUPPORTED_SWAP_CHAINS:
        raise ValueError(f"Chaîne non supportée: {chain}")
    if not is_evm_swap_chain(chain):
        raise ValueError(f"Chaîne non EVM: {chain}")
    meta = SUPPORTED_SWAP_ASSETS[sym]
    if chain not in meta.get("chains", []):
        raise ValueError(f"{sym} indisponible sur {chain}")
    addresses = meta.get("addresses") or {}
    token_address = addresses.get(chain)
    if not token_address:
        raise ValueError(f"Adresse token manquante pour {sym}@{chain}")
    chain_meta = SUPPORTED_SWAP_CHAINS[chain]
    return ResolvedSwapToken(
        asset=sym,
        chain_key=chain,
        lifi_chain_id=chain_meta["lifi_chain_id"],
        token_address=token_address,
        decimals=int(meta["decimals"]),
        display_name=str(meta.get("display_name") or sym),
    )


def human_amount_to_atomic(amount: Decimal, decimals: int) -> str:
    if amount <= 0:
        raise ValueError("Montant invalide")
    scaled = amount * (Decimal(10) ** decimals)
    if scaled != scaled.to_integral_value():
        raise ValueError("Trop de décimales pour l'actif")
    return str(int(scaled))


def atomic_amount_to_human(amount_atomic: str | int, decimals: int) -> Decimal:
    raw = Decimal(str(amount_atomic))
    return raw / (Decimal(10) ** decimals)


def effective_swap_v1_chain_keys() -> frozenset[str]:
    """Chaînes exposées en V1 (pilote : Base uniquement par défaut)."""
    pilot = swap_v1_pilot_chains()
    return SWAP_V1_EVM_CHAIN_KEYS & pilot


def _asset_public_payload(symbol: str, meta: dict[str, Any]) -> dict[str, Any]:
    allowed_chains = effective_swap_v1_chain_keys()
    evm_chains = [
        chain
        for chain in (meta.get("chains") or [])
        if is_evm_swap_chain(chain) and chain in allowed_chains
    ]
    return {
        "symbol": symbol,
        "display_name": meta.get("display_name", symbol),
        "kind": meta.get("kind"),
        "chains": evm_chains,
        "decimals": meta.get("decimals"),
        "min_amount": str(DEFAULT_MIN_SWAP_AMOUNT.get(symbol, Decimal("1"))),
        "max_amount": str(DEFAULT_MAX_SWAP_AMOUNT.get(symbol, Decimal("100000"))),
    }


def list_supported_source_assets_public() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for symbol in sorted(SWAP_V1_SOURCE_ASSETS):
        meta = SUPPORTED_SWAP_ASSETS.get(symbol)
        if meta:
            items.append(_asset_public_payload(symbol, meta))
    return items


def list_supported_destination_assets_public() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for symbol in sorted(SWAP_V1_DESTINATION_ASSETS):
        meta = SUPPORTED_SWAP_ASSETS.get(symbol)
        if meta:
            items.append(_asset_public_payload(symbol, meta))
    return items


def list_supported_assets_public() -> list[dict[str, Any]]:
    return list_supported_source_assets_public()


def list_supported_chains_public() -> list[dict[str, Any]]:
    allowed = effective_swap_v1_chain_keys()
    return [
        {
            "key": key,
            "display_name": meta["display_name"],
            "evm": True,
        }
        for key, meta in SUPPORTED_SWAP_CHAINS.items()
        if key in allowed
    ]
