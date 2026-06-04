"""Actifs autorisés sur Base (portail, marchés, swap Li.FI same-chain).

Source de vérité produit — symboles canoniques en MAJUSCULES (CBBTC, pas cbBTC).
"""
from __future__ import annotations

from typing import TypedDict


class BaseAllowedAsset(TypedDict):
    symbol: str
    name: str
    provider_symbol: str
    decimals: int
    kind: str
    """Adresse ERC-20 sur Base (8453) ; absente si pas de listing on-chain fiable."""
    base_token_address: str | None
    """Éligible au swap Li.FI same-chain sur Base."""
    swap_enabled: bool


# Adresse native Li.FI / EVM
EVM_NATIVE_TOKEN = "0x0000000000000000000000000000000000000000"

BASE_CHAIN_KEY = "base"
BASE_LIFI_CHAIN_ID = 8453

BASE_ALLOWED_ASSETS: tuple[BaseAllowedAsset, ...] = (
    {
        "symbol": "ETH",
        "name": "Ethereum",
        "provider_symbol": "ETHUSDT",
        "decimals": 18,
        "kind": "native",
        "base_token_address": EVM_NATIVE_TOKEN,
        "swap_enabled": True,
    },
    {
        "symbol": "CBETH",
        "name": "Ethereum",
        "provider_symbol": "ETHUSDT",
        "decimals": 18,
        "kind": "wrapped_eth",
        "base_token_address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
        "swap_enabled": True,
    },
    {
        "symbol": "USDC",
        "name": "USD Coin",
        "provider_symbol": "USDCUSDT",
        "decimals": 6,
        "kind": "stablecoin",
        "base_token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "swap_enabled": True,
    },
    {
        "symbol": "EURC",
        "name": "Euro Coin",
        "provider_symbol": "EURUSDT",
        "decimals": 6,
        "kind": "stablecoin",
        "base_token_address": "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42",
        "swap_enabled": True,
    },
    {
        "symbol": "CBBTC",
        "name": "Bitcoin",
        "provider_symbol": "BTCUSDT",
        "decimals": 8,
        "kind": "wrapped_btc",
        "base_token_address": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
        "swap_enabled": True,
    },
    {
        "symbol": "LINK",
        "name": "Chainlink",
        "provider_symbol": "LINKUSDT",
        "decimals": 18,
        "kind": "token",
        "base_token_address": "0x88fb150bdc53a65fe94dea0c9ba0a6daf8c6e196",
        "swap_enabled": True,
    },
    {
        "symbol": "AAVE",
        "name": "Aave",
        "provider_symbol": "AAVEUSDT",
        "decimals": 18,
        "kind": "token",
        "base_token_address": "0x63706e401c06ac8513145b7687a14804d17f814b",
        "swap_enabled": True,
    },
    {
        "symbol": "UNI",
        "name": "Uniswap",
        "provider_symbol": "UNIUSDT",
        "decimals": 18,
        "kind": "token",
        "base_token_address": "0xc3de830ea07524a0761646a6a4e4be0e114a3c83",
        "swap_enabled": True,
    },
)

BASE_ALLOWED_SYMBOLS: frozenset[str] = frozenset(a["symbol"] for a in BASE_ALLOWED_ASSETS)
BASE_SWAP_SYMBOLS: frozenset[str] = frozenset(
    a["symbol"] for a in BASE_ALLOWED_ASSETS if a["swap_enabled"]
)
# Paires Binance uniques pour marchés / top-movers / all-crypto (ordre stable).
BASE_MARKET_PROVIDER_SYMBOLS: tuple[str, ...] = tuple(
    dict.fromkeys(a["provider_symbol"] for a in BASE_ALLOWED_ASSETS)
)

_BASE_DECIMALS_BY_SYMBOL: dict[str, int] = {a["symbol"]: int(a["decimals"]) for a in BASE_ALLOWED_ASSETS}


def base_token_decimals(symbol: str) -> int | None:
    """Décimales ERC-20 / natif sur Base (8453) — source produit swap / ledger on-chain."""
    return _BASE_DECIMALS_BY_SYMBOL.get((symbol or "").strip().upper())
