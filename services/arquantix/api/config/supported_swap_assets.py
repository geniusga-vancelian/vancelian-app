"""Whitelist stricte des actifs et chaînes autorisés pour les swaps LI.FI V1.

V1 scope : EVM uniquement — USDC, USDT, ETH (source et destination).
Aucune adresse de contrat côté front — source de vérité backend uniquement.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Union

from services.lifi.config import swap_v1_pilot_chains

# Adresse native EVM (LI.FI convention).
EVM_NATIVE_TOKEN = "0x0000000000000000000000000000000000000000"

# V1 — périmètre produit (EVM, 3 jetons).
SWAP_V1_EVM_CHAIN_KEYS: frozenset[str] = frozenset({"ethereum", "arbitrum", "base", "polygon"})
SWAP_V1_SOURCE_ASSETS: frozenset[str] = frozenset({"USDC", "USDT", "ETH"})
SWAP_V1_DESTINATION_ASSETS: frozenset[str] = frozenset({"USDC", "USDT", "ETH"})

SUPPORTED_SWAP_CHAINS: dict[str, dict[str, Any]] = {
    "ethereum": {
        "lifi_chain_id": 1,
        "display_name": "Ethereum",
        "wallet_chain_type": "ethereum",
        "evm": True,
    },
    "arbitrum": {
        "lifi_chain_id": 42161,
        "display_name": "Arbitrum",
        "wallet_chain_type": "ethereum",
        "evm": True,
    },
    "base": {
        "lifi_chain_id": 8453,
        "display_name": "Base",
        "wallet_chain_type": "ethereum",
        "evm": True,
    },
    "polygon": {
        "lifi_chain_id": 137,
        "display_name": "Polygon",
        "wallet_chain_type": "ethereum",
        "evm": True,
    },
}

# Montants min/max en unités humaines (pas wei).
DEFAULT_MIN_SWAP_AMOUNT: dict[str, Decimal] = {
    "ETH": Decimal("0.001"),
    "USDC": Decimal("5"),
    "USDT": Decimal("5"),
}

DEFAULT_MAX_SWAP_AMOUNT: dict[str, Decimal] = {
    "ETH": Decimal("50"),
    "USDC": Decimal("250000"),
    "USDT": Decimal("250000"),
}

SUPPORTED_SWAP_ASSETS: dict[str, dict[str, Any]] = {
    "USDC": {
        "display_name": "USD Coin",
        "symbol": "USDC",
        "decimals": 6,
        "kind": "stablecoin",
        "chains": ["ethereum", "arbitrum", "base", "polygon"],
        "addresses": {
            "ethereum": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "polygon": "0x3c499c542cEF5E3811e1192ae670659704471293",
        },
    },
    "USDT": {
        "display_name": "Tether",
        "symbol": "USDT",
        "decimals": 6,
        "kind": "stablecoin",
        "chains": ["ethereum", "arbitrum", "base", "polygon"],
        "addresses": {
            "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "base": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
            "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        },
    },
    "ETH": {
        "display_name": "Ethereum",
        "symbol": "ETH",
        "decimals": 18,
        "kind": "native",
        "chains": ["ethereum", "arbitrum", "base", "polygon"],
        "addresses": {
            "ethereum": EVM_NATIVE_TOKEN,
            "arbitrum": EVM_NATIVE_TOKEN,
            "base": EVM_NATIVE_TOKEN,
            "polygon": EVM_NATIVE_TOKEN,
        },
    },
}


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
    return aliases.get(key, key)


def normalize_asset_symbol(asset: str) -> str:
    return (asset or "").strip().upper()


def is_evm_swap_chain(chain_key: str) -> bool:
    chain = normalize_chain_key(chain_key)
    return chain in SWAP_V1_EVM_CHAIN_KEYS


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
    """Chaînes exposées en V1 (pilote : Base + Ethereum mainnet par défaut)."""
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
    """Actifs éligibles en wallet source (V1 : USDC, USDT, ETH — EVM)."""
    items: list[dict[str, Any]] = []
    for symbol in sorted(SWAP_V1_SOURCE_ASSETS):
        meta = SUPPORTED_SWAP_ASSETS.get(symbol)
        if meta:
            items.append(_asset_public_payload(symbol, meta))
    return items


def list_supported_destination_assets_public() -> list[dict[str, Any]]:
    """Actifs éligibles en destination (V1 : USDC, USDT, ETH — EVM)."""
    items: list[dict[str, Any]] = []
    for symbol in sorted(SWAP_V1_DESTINATION_ASSETS):
        meta = SUPPORTED_SWAP_ASSETS.get(symbol)
        if meta:
            items.append(_asset_public_payload(symbol, meta))
    return items


def list_supported_assets_public() -> list[dict[str, Any]]:
    """Alias rétrocompat — liste complète swappable V1 (= source assets)."""
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
