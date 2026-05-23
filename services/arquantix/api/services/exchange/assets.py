"""Central asset registry for the Exchange module.

Defines supported assets, precision rules, and provider symbol mappings.
Settlement wallet reserves are v1 in-memory placeholders — production
will sync from Fireblocks.
"""
from __future__ import annotations

from decimal import Decimal

SUPPORTED_ASSETS: set[str] = {
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "BNB", "DOGE", "AVAX", "LINK", "DOT",
    "USDC", "USDT", "EURC",
}

ASSET_PRECISION: dict[str, int] = {
    "BTC": 8,
    "ETH": 18,
    "SOL": 9,
    "XRP": 6,
    "ADA": 6,
    "BNB": 8,
    "DOGE": 8,
    "AVAX": 8,
    "LINK": 8,
    "DOT": 8,
    "USDC": 6,
    "USDT": 6,
    "EURC": 6,
}

ASSET_PROVIDER_SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "DOT": "DOTUSDT",
    "USDC": "USDCUSDT",
    # EURC: no Binance pair exists (EURCUSDT is invalid).
    # Pricing uses EUR-pegged fallback (1 EURC = 1 EUR) in _resolve_price().
}

# ---------------------------------------------------------------------------
# Settlement wallet reserves (v1: in-memory, production: Fireblocks sync)
# ---------------------------------------------------------------------------

_settlement_wallet_reserves: dict[str, Decimal] = {}


def get_settlement_wallet_balance(asset: str) -> Decimal:
    """Return the company settlement wallet balance for *asset*.

    In production this will query Fireblocks vault accounts.
    """
    return _settlement_wallet_reserves.get(asset, Decimal("0"))


def set_settlement_wallet_balance(asset: str, balance: Decimal) -> None:
    """Seed or update the settlement wallet reserve for *asset* (v1 helper)."""
    _settlement_wallet_reserves[asset] = balance


def clear_settlement_wallet_balances() -> None:
    """Reset all reserves (useful in tests)."""
    _settlement_wallet_reserves.clear()
