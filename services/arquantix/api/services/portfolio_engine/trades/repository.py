"""Repository layer for pe_trades (Portfolio Engine — transaction layer).

INSERT-ONLY: no update or delete methods are provided.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Trade


class TradeRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Trade:
        trade = Trade(**data)
        db.add(trade)
        db.flush()
        return trade

    @staticmethod
    def get_by_id(db: Session, trade_id: UUID) -> Optional[Trade]:
        return db.query(Trade).filter(Trade.id == trade_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        instrument_id: Optional[UUID] = None,
        side: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Trade], int]:
        query = db.query(Trade)
        if order_id:
            query = query.filter(Trade.order_id == order_id)
        if instrument_id:
            query = query.filter(Trade.instrument_id == instrument_id)
        if side:
            query = query.filter(Trade.side == side)
        total = query.count()
        items = query.order_by(Trade.executed_at.desc()).offset(skip).limit(limit).all()
        return items, total
