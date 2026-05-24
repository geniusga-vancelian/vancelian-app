"""Wallets Privy dédiés à une chaîne (hors EVM multi-actifs) → actif natif affiché."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import SUPPORTED_ASSETS
from services.privy_wallet.repository import PersonCryptoWalletRepository
from services.test_clients.schemas import ASSET_NAMES

# Chaînes « wallet dédié » (1 actif natif) — exclut EVM où ETH/USDC/USDT coexistent.
DEDICATED_WALLET_NATIVE_ASSET: dict[str, str] = {
    "solana": "SOL",
    "sol": "SOL",
    "bitcoin": "BTC",
    "bitcoin-segwit": "BTC",
    "bitcoin-taproot": "BTC",
    "xrp": "XRP",
    "cosmos": "ATOM",
    "stellar": "XLM",
    "sui": "SUI",
    "aptos": "APT",
    "ton": "TON",
    "near": "NEAR",
    "tron": "TRX",
}


def is_evm_wallet_chain(chain_type: str | None) -> bool:
    chain = (chain_type or "").strip().lower()
    return chain in ("evm", "ethereum")


def native_asset_for_dedicated_wallet(chain_type: str | None) -> str | None:
    """Retourne le ticker natif pour un wallet dédié non-EVM, ou ``None``."""
    if is_evm_wallet_chain(chain_type):
        return None
    chain = (chain_type or "").strip().lower()
    asset = DEDICATED_WALLET_NATIVE_ASSET.get(chain)
    if not asset:
        return None
    asset_u = asset.upper()
    if asset_u not in SUPPORTED_ASSETS:
        return None
    return asset_u


def dedicated_wallet_placeholders_for_person(
    db: Session,
    *,
    person_id: UUID,
    exclude_assets: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Placeholders balance 0 pour chaque wallet dédié actif sans solde positif connu."""
    excluded = {a.upper() for a in (exclude_assets or set())}
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    seen_assets: set[str] = set()
    out: list[dict[str, Any]] = []

    for wallet in wallets:
        asset = native_asset_for_dedicated_wallet(wallet.chain_type)
        if not asset or asset in excluded or asset in seen_assets:
            continue
        seen_assets.add(asset)
        out.append(
            {
                "asset": asset,
                "name": ASSET_NAMES.get(asset, asset),
                "balance": "0",
                "available_balance": "0",
                "platform_balance": "0",
                "platform_available": "0",
                "privy_balance": "0",
                "privy_available": "0",
                "price_eur": None,
                "estimated_value_eur": None,
                "price_usd": None,
                "estimated_value_usd": None,
                "performance_1d_pct": None,
                "icon_key": asset.lower(),
                "portfolio_scope": "privy",
                "dedicated_wallet": True,
                "chain_type": wallet.chain_type,
                "wallet_address": wallet.address,
            }
        )
    return out
