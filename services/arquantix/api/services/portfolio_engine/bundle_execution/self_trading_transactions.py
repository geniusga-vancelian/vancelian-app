"""Helpers — périmètre Mon Trading (hors opérations internes bundle)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
    is_bundle_scoped_exchange_order,
    privy_deposit_is_bundle_internal,
    swap_has_strong_bundle_batch_context,
)
from services.privy_wallet.transaction_merge import person_wallet_swap_to_crypto_tx


def exclude_bundle_internal_swaps(swaps: list[Any]) -> list[Any]:
    """Retire les swaps Li.FI exécutés dans un batch bundle."""
    return [
        swap
        for swap in swaps
        if not is_bundle_internal_swap(swap) and not swap_has_strong_bundle_batch_context(swap)
    ]


def filter_self_trading_exchange_orders(orders: list[Any]) -> list[Any]:
    """Retire les ordres exchange taggés portfolio_scope=bundle."""
    return [order for order in orders if not is_bundle_scoped_exchange_order(order)]


def filter_self_trading_privy_deposits(
    db: Session,
    deposits: list[Any],
) -> list[Any]:
    """Retire les dépôts Privy liés à un swap bundle interne."""
    return [
        deposit
        for deposit in deposits
        if not privy_deposit_is_bundle_internal(db, deposit)
    ]


def map_self_trading_lifi_swaps_to_crypto_txs(
    swaps: list[Any],
    *,
    asset: str,
) -> list[dict[str, Any]]:
    """Mappe les swaps Li.FI self-trading vers des lignes d'historique crypto."""
    asset_u = asset.upper()
    txs: list[dict[str, Any]] = []
    for swap in exclude_bundle_internal_swaps(swaps):
        mapped = person_wallet_swap_to_crypto_tx(swap, asset=asset_u)
        if mapped is not None:
            txs.append(mapped)
    return txs


def build_self_trading_lifi_swap_txs(
    db: Session,
    *,
    person_id: UUID,
    asset: str,
    swap_rows: list[Any],
) -> list[dict[str, Any]]:
    """Alias explicite pour l'historique crypto Mon Trading."""
    _ = db, person_id
    return map_self_trading_lifi_swaps_to_crypto_txs(swap_rows, asset=asset)
