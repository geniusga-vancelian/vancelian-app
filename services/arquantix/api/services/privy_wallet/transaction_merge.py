"""Fusion historique transactions crypto : échanges + ledger Privy.

Modèle cible : Privy est le custody privilégié du client — toute crypto détenue
(credit exchange euro→crypto, swap crypto→crypto via LI.fi, dépôt on-chain) se
matérialise sur son wallet Privy. La base ``person_wallet_*`` doit rester
réconciliée avec l’état on-chain (webhooks + reconcile périodique).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

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


def person_wallet_swap_to_crypto_tx(swap: Any, *, asset: str) -> dict[str, Any] | None:
    """Mappe un swap LI.FI confirmé vers une ligne d'historique pour l'actif consulté."""
    asset_u = asset.strip().upper()
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    if asset_u not in {from_asset, to_asset}:
        return None

    amount_in = _format_decimal(swap.amount_in)
    amount_out = _format_decimal(swap.estimated_receive)
    is_outgoing = asset_u == from_asset
    amount_crypto = amount_in if is_outgoing else amount_out
    direction = "debit" if is_outgoing else "credit"
    sign = "-" if is_outgoing else "+"
    chain_label = str(swap.from_chain or "").strip().capitalize()
    if swap.from_chain == swap.to_chain and chain_label:
        chain_suffix = f" · {chain_label}"
    else:
        chain_suffix = f" · {swap.from_chain} → {swap.to_chain}"

    return {
        "id": swap.id,
        "side": "swap",
        "asset": asset_u,
        "amount_crypto": amount_crypto,
        "amount_fiat": "0",
        "price": "0",
        "currency": "EUR",
        "status": "confirmed",
        "fee_amount": _format_decimal(swap.vancelian_fee) if swap.vancelian_fee else None,
        "fee_asset": swap.from_asset if swap.vancelian_fee else None,
        "external_reference": swap.tx_hash,
        "created_at": swap.confirmed_at or swap.created_at,
        "title": f"Échange {from_asset} → {to_asset}",
        "subtitle": f"{sign}{amount_crypto} {asset_u}{chain_suffix}",
        "direction": direction,
        "from_asset": from_asset,
        "to_asset": to_asset,
        "transaction_kind": "crypto_swap",
        "source_system": "lifi_swap",
        "tx_hash": swap.tx_hash,
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
    extra_txs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Fusionne et trie par date décroissante."""
    merged = list(exchange_txs) + [privy_deposit_to_crypto_tx(row) for row in privy_rows]
    if extra_txs:
        seen = {str(tx.get("id")) for tx in merged if tx.get("id") is not None}
        for tx in extra_txs:
            tx_id = tx.get("id")
            if tx_id is not None and str(tx_id) in seen:
                continue
            merged.append(tx)
            if tx_id is not None:
                seen.add(str(tx_id))
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


def list_orphan_webhook_crypto_txs(
    db: Session,
    *,
    person_id: UUID,
    asset: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Reconstitue les dépôts Privy lorsque le ledger a perdu la ligne mais le webhook est processed."""
    from services.privy_wallet.asset_mapping import format_amount_display
    from services.privy_wallet.enums import PrivyWebhookEventStatus
    from services.privy_wallet.models import PrivyWebhookEvent
    from services.privy_wallet.repository import PersonCryptoWalletRepository
    from services.privy_wallet.webhook_service import PrivyWebhookProcessor

    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    if not wallets:
        return []
    addresses = {w.address.lower() for w in wallets}
    asset_u = asset.upper() if asset else None

    events = (
        db.query(PrivyWebhookEvent)
        .filter(
            PrivyWebhookEvent.processing_status == PrivyWebhookEventStatus.PROCESSED.value,
            PrivyWebhookEvent.event_type == "wallet.funds_deposited",
            PrivyWebhookEvent.linked_deposit_id.isnot(None),
        )
        .order_by(PrivyWebhookEvent.received_at.desc())
        .limit(max(limit * 4, 50))
        .all()
    )

    txs: list[dict[str, Any]] = []
    for event in events:
        linked_id = event.linked_deposit_id
        if linked_id is None:
            continue
        deposit_exists = (
            db.query(PersonWalletDeposit.id)
            .filter(PersonWalletDeposit.id == linked_id)
            .first()
        )
        if deposit_exists:
            continue

        try:
            normalized = PrivyWebhookProcessor._normalize_deposit_payload(event.payload_raw)
        except Exception:
            continue

        if normalized.to_address not in addresses:
            continue
        if asset_u and normalized.asset.upper() != asset_u:
            continue

        amount = _format_decimal(normalized.amount)
        chain_label = normalized.chain_type.upper()
        if normalized.chain_id is not None:
            chain_label = f"{chain_label} ({normalized.chain_id})"
        amount_display = format_amount_display(normalized.amount, normalized.asset)
        asset_name = ASSET_NAMES.get(normalized.asset, normalized.asset)

        txs.append(
            {
                "id": linked_id,
                "side": "deposit",
                "asset": normalized.asset,
                "amount_crypto": amount,
                "amount_fiat": "0",
                "price": "0",
                "currency": "EUR",
                "status": "confirmed",
                "fee_amount": None,
                "fee_asset": None,
                "external_reference": normalized.tx_hash,
                "created_at": event.received_at,
                "title": f"Dépôt {asset_name}",
                "subtitle": f"+{amount_display} {normalized.asset} · Wallet Privy · {chain_label}",
                "direction": "credit",
                "from_asset": None,
                "to_asset": normalized.asset,
                "transaction_kind": "privy_deposit_in",
                "source_system": "privy",
                "tx_hash": normalized.tx_hash,
                "custody_provider": "privy",
            }
        )
        if len(txs) >= limit:
            break

    return txs
