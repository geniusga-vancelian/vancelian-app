"""Whitelist LI.FI dédiée aux bundles — Base uniquement (Phase 2).

Séparée de ``config.supported_swap_assets`` (portail swap V1) pour ne pas
élargir le self-trading sans décision produit explicite.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from config.supported_swap_assets import EVM_NATIVE_TOKEN, SUPPORTED_SWAP_CHAINS

BUNDLE_LIFI_CHAIN_KEY = "base"

BUNDLE_LIFI_SOURCE_ASSETS: frozenset[str] = frozenset({"USDC", "EURC", "ETH"})
BUNDLE_LIFI_DESTINATION_ASSETS: frozenset[str] = frozenset({"USDC", "EURC", "ETH", "CBBTC"})

# Coinbase Wrapped BTC on Base mainnet (canonical).
CBBTC_BASE_ADDRESS = "0xcbB7c0000aB88B473b1f5aFd9ef808440eed33Bf"

# Circle EURC on Base.
EURC_BASE_ADDRESS = "0x60a3E35Cc106573386850dcfc71F6a032A550f1"

BUNDLE_BASE_ASSETS: dict[str, dict[str, Any]] = {
    "USDC": {
        "display_name": "USD Coin",
        "decimals": 6,
        "kind": "stablecoin",
        "addresses": {"base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
    },
    "EURC": {
        "display_name": "Euro Coin",
        "decimals": 6,
        "kind": "stablecoin",
        "addresses": {"base": EURC_BASE_ADDRESS},
    },
    "ETH": {
        "display_name": "Ethereum",
        "decimals": 18,
        "kind": "native",
        "addresses": {"base": EVM_NATIVE_TOKEN},
    },
    "CBBTC": {
        "display_name": "Coinbase Wrapped BTC",
        "decimals": 8,
        "kind": "wrapped_btc",
        "addresses": {"base": CBBTC_BASE_ADDRESS},
    },
}

DEFAULT_BUNDLE_MIN: dict[str, Decimal] = {
    "USDC": Decimal("5"),
    "EURC": Decimal("5"),
    "ETH": Decimal("0.001"),
    "CBBTC": Decimal("0.00001"),
}

# Mapping symboles PE / Exchange → symbole swap Base
PE_ASSET_TO_BUNDLE_LIFI: dict[str, str] = {
    "BTC": "CBBTC",
    "TBTC": "CBBTC",
    "BTC_CB": "CBBTC",
    "ETH": "ETH",
    "TETH": "ETH",
    "USDC": "USDC",
    "EURC": "EURC",
}


@dataclass(frozen=True)
class BundleBaseToken:
    asset: str
    chain_key: str
    lifi_chain_id: int
    token_address: str
    decimals: int


def normalize_bundle_asset(asset: str) -> str:
    upper = (asset or "").strip().upper()
    return PE_ASSET_TO_BUNDLE_LIFI.get(upper, upper)


def resolve_bundle_base_token(asset: str) -> BundleBaseToken:
    sym = normalize_bundle_asset(asset)
    if sym not in BUNDLE_BASE_ASSETS:
        raise ValueError(f"Asset bundle Base non supporté: {asset}")
    meta = BUNDLE_BASE_ASSETS[sym]
    chain_meta = SUPPORTED_SWAP_CHAINS[BUNDLE_LIFI_CHAIN_KEY]
    address = meta["addresses"]["base"]
    return BundleBaseToken(
        asset=sym,
        chain_key=BUNDLE_LIFI_CHAIN_KEY,
        lifi_chain_id=int(chain_meta["lifi_chain_id"]),
        token_address=address,
        decimals=int(meta["decimals"]),
    )


def is_bundle_lifi_asset(asset: str) -> bool:
    sym = normalize_bundle_asset(asset)
    return sym in BUNDLE_BASE_ASSETS


def validate_bundle_leg_assets(from_asset: str, to_asset: str) -> None:
    from_sym = normalize_bundle_asset(from_asset)
    to_sym = normalize_bundle_asset(to_asset)
    if from_sym == to_sym:
        raise ValueError("same_asset")
    if from_sym not in BUNDLE_LIFI_SOURCE_ASSETS:
        raise ValueError(f"source_not_allowed:{from_sym}")
    if to_sym not in BUNDLE_LIFI_DESTINATION_ASSETS:
        raise ValueError(f"destination_not_allowed:{to_sym}")
