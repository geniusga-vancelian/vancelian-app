"""Fusion historique transactions crypto : échanges + ledger Privy.

Modèle cible : Privy est le custody privilégié du client — toute crypto détenue
(credit exchange euro→crypto, swap crypto→crypto via LI.fi, dépôt on-chain) se
matérialise sur son wallet Privy. La base ``person_wallet_*`` doit rester
réconciliée avec l’état on-chain (webhooks + reconcile périodique).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.service import _format_decimal
from services.test_clients.schemas import ASSET_NAMES


def exchange_order_to_crypto_tx(order: Any, *, asset: str) -> dict[str, Any]:
    """Mappe un ``ExchangeOrder`` vers un dict ``CryptoTransactionPayload``."""
    is_swap = (
        order.from_asset is not None
        and order.to_asset is not None
        and order.from_asset != order.currency
    )
    from_a = order.from_asset or (order.currency if order.side == "buy" else asset)
    to_a = order.to_asset or (asset if order.side == "buy" else order.currency)

    if is_swap:
        side_label = f"{from_a} → {to_a}"
    else:
        side_label = "Achat" if order.side == "buy" else "Vente"
    title = (
        f"{side_label} {ASSET_NAMES.get(asset, asset)}"
        if not is_swap
        else side_label
    )
    subtitle = (
        f"{order.amount_fiat:.2f} EUR"
        if order.side == "buy"
        else f"{order.amount_crypto} {asset}"
    )
    direction = "credit" if order.side == "buy" else "debit"

    return {
        "id": order.id,
        "side": order.side,
        "asset": order.asset,
        "amount_crypto": f"{order.amount_crypto}",
        "amount_fiat": f"{order.amount_fiat:.2f}",
        "price": f"{order.price:.2f}",
        "currency": order.currency,
        "status": order.status,
        "fee_amount": f"{order.fee_amount}" if order.fee_amount else None,
        "fee_asset": order.fee_asset,
        "external_reference": order.external_reference,
        "created_at": order.created_at,
        "title": title,
        "subtitle": subtitle,
        "direction": direction,
        "from_asset": order.from_asset,
        "to_asset": order.to_asset,
        "transaction_kind": f"exchange_{order.side}",
        "source_system": "exchange",
        "tx_hash": None,
        "custody_provider": "privy",
    }


def privy_deposit_to_crypto_tx(row: PersonWalletDeposit) -> dict[str, Any]:
    """Mappe un dépôt ledger Privy vers un dict ``CryptoTransactionPayload``."""
    amount = _format_decimal(row.amount)
    chain_label = row.chain_type.upper()
    if row.chain_id is not None:
        chain_label = f"{chain_label} ({row.chain_id})"

    return {
        "id": row.id,
        "side": "deposit",
        "asset": row.asset,
        "amount_crypto": amount,
        "amount_fiat": "0",
        "price": "0",
        "currency": "EUR",
        "status": row.status,
        "fee_amount": None,
        "fee_asset": None,
        "external_reference": row.tx_hash,
        "created_at": row.created_at,
        "title": row.title,
        "subtitle": row.subtitle or f"Wallet Privy · {chain_label}",
        "direction": row.direction,
        "from_asset": None,
        "to_asset": row.asset,
        "transaction_kind": row.transaction_kind,
        "source_system": "privy",
        "tx_hash": row.tx_hash,
        "custody_provider": "privy",
    }


def merge_crypto_transactions(
    exchange_txs: list[dict[str, Any]],
    privy_rows: list[PersonWalletDeposit],
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Fusionne et trie par date décroissante."""
    merged = list(exchange_txs) + [privy_deposit_to_crypto_tx(row) for row in privy_rows]
    merged.sort(key=_tx_sort_key, reverse=True)
    return merged[:limit]


def _tx_sort_key(tx: dict[str, Any]) -> datetime:
    created = tx.get("created_at")
    if isinstance(created, datetime):
        return created
    if isinstance(created, str):
        try:
            return datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=None)
