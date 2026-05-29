"""Ingestion exchange_orders → cost_basis_executions (idempotent)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.ingest import record_execution
from services.cost_basis.valuation import build_frozen_valuation
from services.exchange.models import ExchangeOrder
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_scoped_exchange_order,
)


def _dec(v: object) -> Decimal:
    return Decimal(str(v))


def _order_executed_at(order: ExchangeOrder) -> datetime:
    ts = order.created_at
    if ts is None:
        return datetime.now(timezone.utc)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def _portfolio_meta(order: ExchangeOrder) -> tuple[Optional[str], Optional[UUID]]:
    meta = order.metadata_ if isinstance(order.metadata_, dict) else {}
    scope = meta.get("portfolio_scope")
    pid = meta.get("portfolio_id")
    portfolio_id = UUID(str(pid)) if pid else None
    if is_bundle_scoped_exchange_order(order):
        return "bundle", portfolio_id
    if scope == "direct":
        return "direct", portfolio_id
    return "direct", portfolio_id


def ingest_exchange_order(db: Session, order: ExchangeOrder) -> bool:
    """Ingère un ordre exchange complété. Retourne True si nouvelle ligne créée."""
    if str(order.status).lower() != "completed":
        return False

    side = str(order.side).lower()
    asset = str(order.asset).upper()
    qty = _dec(order.amount_crypto)
    if qty <= 0:
        return False

    executed = _order_executed_at(order)
    scope, portfolio_id = _portfolio_meta(order)

    is_swap = (
        order.from_asset is not None
        and order.to_asset is not None
        and str(order.from_asset).upper() != str(order.currency or "EUR").upper()
    )

    if side == "buy":
        if is_swap:
            quote_asset = str(order.from_asset).upper()
            quote_amount = _dec(order.amount_from) if order.amount_from else _dec(order.amount_fiat)
            fee = _dec(order.fee_amount) if order.fee_amount else Decimal("0")
            valuation = build_frozen_valuation(
                db,
                position_asset=asset,
                quantity=qty,
                quote_asset=quote_asset,
                quote_amount=quote_amount,
                fee_quote_amount=fee,
                executed_at=executed,
            )
        else:
            notional_eur = _dec(order.amount_fiat)
            fee_eur = _dec(order.fee_amount) if order.fee_amount else Decimal("0")
            valuation = build_frozen_valuation(
                db,
                position_asset=asset,
                quantity=qty,
                quote_asset="EUR",
                quote_amount=notional_eur,
                fee_quote_amount=fee_eur,
                executed_at=executed,
            )

        return record_execution(
            db,
            client_id=order.client_id,
            person_id=None,
            position_asset=asset,
            event_kind="acquisition",
            quantity=qty,
            valuation=valuation,
            provider_source="exchange",
            provider_execution_id=f"exchange:{order.id}",
            executed_at=executed,
            tx_hash=None,
            counterparty_asset=str(order.from_asset or order.currency or "EUR").upper(),
            portfolio_scope=scope,
            portfolio_id=portfolio_id,
            metadata={"exchange_order_id": str(order.id), "side": "buy"},
        ) is not None

    if side == "sell":
        if is_swap:
            quote_asset = str(order.to_asset).upper()
            quote_amount = _dec(order.amount_to) if order.amount_to else _dec(order.amount_fiat)
        else:
            quote_asset = "EUR"
            quote_amount = _dec(order.amount_to) if order.amount_to else _dec(order.amount_fiat)
        fee = _dec(order.fee_amount) if order.fee_amount else Decimal("0")
        valuation = build_frozen_valuation(
            db,
            position_asset=asset,
            quantity=qty,
            quote_asset=quote_asset,
            quote_amount=quote_amount,
            fee_quote_amount=fee,
            executed_at=executed,
        )
        return record_execution(
            db,
            client_id=order.client_id,
            person_id=None,
            position_asset=asset,
            event_kind="disposal",
            quantity=qty,
            valuation=valuation,
            provider_source="exchange",
            provider_execution_id=f"exchange:{order.id}",
            executed_at=executed,
            tx_hash=None,
            counterparty_asset=str(order.to_asset or order.currency or "EUR").upper(),
            portfolio_scope=scope,
            portfolio_id=portfolio_id,
            metadata={"exchange_order_id": str(order.id), "side": "sell"},
        ) is not None

    return False


def backfill_exchange_orders_for_client_asset(
    db: Session,
    client_id: UUID,
    asset: str,
) -> int:
    """Backfill idempotent des ordres historiques pour un actif."""
    from services.portfolio_engine.bundle_execution.self_trading_transactions import (
        filter_self_trading_exchange_orders,
    )

    orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client_id,
            ExchangeOrder.asset == asset.upper(),
            ExchangeOrder.status == "completed",
        )
        .order_by(ExchangeOrder.created_at.asc())
        .all()
    )
    orders = filter_self_trading_exchange_orders(orders)
    count = 0
    for order in orders:
        if ingest_exchange_order(db, order):
            count += 1
    return count
