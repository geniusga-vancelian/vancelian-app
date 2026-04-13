"""Repository layer for Exchange module tables."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from .models import CryptoPosition, CryptoSettlementDelta, ExchangeFeeConfig, ExchangeOrder


class CryptoPositionRepository:

    @staticmethod
    def get_or_create_for_update(db: Session, client_id: UUID, asset: str) -> CryptoPosition:
        """Fetch (or create) the position row with a row-level lock (SELECT … FOR UPDATE)."""
        pos = (
            db.query(CryptoPosition)
            .filter(CryptoPosition.client_id == client_id, CryptoPosition.asset == asset)
            .with_for_update()
            .first()
        )
        if pos is None:
            pos = CryptoPosition(
                client_id=client_id,
                asset=asset,
                balance=Decimal("0"),
                available_balance=Decimal("0"),
            )
            db.add(pos)
            db.flush()
            # Re-lock after insert to guarantee exclusive hold within the tx
            pos = (
                db.query(CryptoPosition)
                .filter(CryptoPosition.id == pos.id)
                .with_for_update()
                .first()
            )
        return pos

    @staticmethod
    def get_aggregate_balance(db: Session, asset: str) -> Decimal:
        """Return the total client-held balance for *asset* (clients pool)."""
        result = (
            db.query(func.coalesce(func.sum(CryptoPosition.balance), 0))
            .filter(CryptoPosition.asset == asset)
            .scalar()
        )
        return Decimal(str(result))

    @staticmethod
    def credit(db: Session, position: CryptoPosition, amount: Decimal) -> CryptoPosition:
        position.balance = Decimal(str(position.balance)) + amount
        position.available_balance = Decimal(str(position.available_balance)) + amount
        position.updated_at = func.now()
        db.flush()
        return position

    @staticmethod
    def debit(db: Session, position: CryptoPosition, amount: Decimal) -> CryptoPosition:
        """Subtract *amount* from the position. Raises ValueError if insufficient."""
        current = Decimal(str(position.balance))
        if current < amount:
            raise ValueError(
                f"insufficient_crypto_balance: available={current}, requested={amount}"
            )
        position.balance = current - amount
        position.available_balance = Decimal(str(position.available_balance)) - amount
        position.updated_at = func.now()
        db.flush()
        return position

    @staticmethod
    def list_by_client(db: Session, client_id: UUID) -> list[CryptoPosition]:
        return (
            db.query(CryptoPosition)
            .filter(CryptoPosition.client_id == client_id)
            .order_by(CryptoPosition.asset)
            .all()
        )


class ExchangeFeeConfigRepository:

    @staticmethod
    def get_active_fee_bps(db: Session, asset: str) -> int:
        """Return the active fee in basis points for *asset*, or 0 if none configured."""
        row = (
            db.query(ExchangeFeeConfig)
            .filter(ExchangeFeeConfig.asset == asset, ExchangeFeeConfig.active.is_(True))
            .first()
        )
        return row.fee_bps if row else 0

    @staticmethod
    def get_active_spread_bps(db: Session, asset: str) -> int:
        """Return the active spread in basis points for *asset*, default 50 (0.50%)."""
        row = (
            db.query(ExchangeFeeConfig)
            .filter(ExchangeFeeConfig.asset == asset, ExchangeFeeConfig.active.is_(True))
            .first()
        )
        return row.spread_bps if row and row.spread_bps else 50

    @staticmethod
    def upsert(db: Session, asset: str, fee_bps: int, spread_bps: int = 50) -> ExchangeFeeConfig:
        row = db.query(ExchangeFeeConfig).filter(ExchangeFeeConfig.asset == asset).first()
        if row is None:
            row = ExchangeFeeConfig(asset=asset, fee_bps=fee_bps, spread_bps=spread_bps, active=True)
            db.add(row)
        else:
            row.fee_bps = fee_bps
            row.spread_bps = spread_bps
            row.active = True
        db.flush()
        return row


class ExchangeOrderRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ExchangeOrder:
        order = ExchangeOrder(**data)
        db.add(order)
        db.flush()
        return order

    @staticmethod
    def list_by_client_asset(db: Session, client_id: UUID, asset: str, *, limit: int = 50) -> list[ExchangeOrder]:
        return (
            db.query(ExchangeOrder)
            .filter(ExchangeOrder.client_id == client_id, ExchangeOrder.asset == asset)
            .order_by(ExchangeOrder.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_client_asset_buy_totals(db: Session, client_id: UUID, asset: str) -> tuple[Decimal, Decimal]:
        """Return (total_fiat_spent, total_crypto_received) for completed buys."""
        row = (
            db.query(
                func.coalesce(func.sum(ExchangeOrder.amount_fiat), 0),
                func.coalesce(func.sum(ExchangeOrder.amount_crypto), 0),
            )
            .filter(
                ExchangeOrder.client_id == client_id,
                ExchangeOrder.asset == asset,
                ExchangeOrder.side == "buy",
                ExchangeOrder.status == "completed",
            )
            .first()
        )
        return (Decimal(str(row[0])), Decimal(str(row[1]))) if row else (Decimal("0"), Decimal("0"))

    @staticmethod
    def get_client_asset_sell_totals(db: Session, client_id: UUID, asset: str) -> tuple[Decimal, Decimal]:
        """Return (total_net_fiat_received, total_crypto_sold) for completed sells.

        Uses amount_to (net EUR) for fiat received when available; falls back to
        amount_fiat - fee_amount for legacy orders. Realized P&L must use net, not gross.
        """
        orders = (
            db.query(ExchangeOrder)
            .filter(
                ExchangeOrder.client_id == client_id,
                ExchangeOrder.asset == asset,
                ExchangeOrder.side == "sell",
                ExchangeOrder.status == "completed",
            )
            .all()
        )
        total_net = Decimal("0")
        total_crypto = Decimal("0")
        for o in orders:
            amt = Decimal(str(o.amount_crypto))
            total_crypto += amt
            if o.amount_to is not None:
                total_net += Decimal(str(o.amount_to))
            else:
                gross = Decimal(str(o.amount_fiat))
                fee = Decimal(str(o.fee_amount)) if o.fee_amount else Decimal("0")
                total_net += gross - fee
        return (total_net, total_crypto)

    @staticmethod
    def get_wac_state_before_sell(
        db: Session, client_id: UUID, asset: str
    ) -> tuple[Decimal, Decimal]:
        """Return (cost_basis_total, position_qty) using WAC from completed orders.

        Iterates orders chronologically. Used to compute avg_cost at SELL time.
        Method: Weighted Average Cost (WAC) — official accounting method.
        """
        orders = (
            db.query(ExchangeOrder)
            .filter(
                ExchangeOrder.client_id == client_id,
                ExchangeOrder.asset == asset,
                ExchangeOrder.status == "completed",
            )
            .order_by(ExchangeOrder.created_at.asc())
            .all()
        )
        cost_basis = Decimal("0")
        position = Decimal("0")
        for o in orders:
            amt = Decimal(str(o.amount_crypto))
            price = Decimal(str(o.price))
            if o.side == "buy":
                cost_basis += amt * price
                position += amt
            else:
                if position > 0:
                    avg_cost = cost_basis / position
                    cost_basis -= amt * avg_cost
                position -= amt
                if position <= 0:
                    position = Decimal("0")
                    cost_basis = Decimal("0")
        return (cost_basis, position)

    @staticmethod
    def find_by_reference(db: Session, external_reference: str) -> ExchangeOrder | None:
        return (
            db.query(ExchangeOrder)
            .filter(ExchangeOrder.external_reference == external_reference)
            .first()
        )

    @staticmethod
    def update_status(
        db: Session,
        order: ExchangeOrder,
        *,
        new_status: str,
        failure_reason: str | None = None,
    ) -> ExchangeOrder:
        order.status = new_status
        if failure_reason is not None:
            order.failure_reason = failure_reason
        db.flush()
        return order


class CryptoSettlementDeltaRepository:

    @staticmethod
    def get_or_create(db: Session, asset: str, settlement_date: date) -> CryptoSettlementDelta:
        delta = (
            db.query(CryptoSettlementDelta)
            .filter(
                CryptoSettlementDelta.asset == asset,
                CryptoSettlementDelta.settlement_date == settlement_date,
            )
            .with_for_update()
            .first()
        )
        if delta is None:
            delta = CryptoSettlementDelta(
                asset=asset,
                settlement_date=settlement_date,
                delta_amount=Decimal("0"),
                settled=False,
            )
            db.add(delta)
            db.flush()
        return delta

    @staticmethod
    def increment(db: Session, delta: CryptoSettlementDelta, amount: Decimal) -> CryptoSettlementDelta:
        delta.delta_amount = Decimal(str(delta.delta_amount)) + amount
        delta.settled = False
        delta.updated_at = func.now()
        db.flush()
        return delta

    @staticmethod
    def list_unsettled(db: Session) -> list[CryptoSettlementDelta]:
        return (
            db.query(CryptoSettlementDelta)
            .filter(CryptoSettlementDelta.settled.is_(False))
            .order_by(CryptoSettlementDelta.settlement_date, CryptoSettlementDelta.asset)
            .all()
        )

    @staticmethod
    def mark_settled(db: Session, delta: CryptoSettlementDelta) -> CryptoSettlementDelta:
        delta.settled = True
        delta.updated_at = func.now()
        db.flush()
        return delta
