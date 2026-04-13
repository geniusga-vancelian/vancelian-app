"""Service layer for Trades module (Portfolio Engine — transaction layer).

Trades are IMMUTABLE once created. This service records trades, updates
order status, and derives position state via PositionService.apply_trade().

Ledger entries are NOT written directly by this service — they flow
through the Settlement layer:

    TradeService.record_trade() → Trade created → Position updated
    SettlementService.create_trade_settlements() → Settlement instructions created
    SettlementService.settle() → Ledger entries written

TODO: Once account resolution is implemented, record_trade() should call
SettlementService.create_trade_settlements() to create settlement instructions
automatically. Currently, settlement creation must be orchestrated explicitly
by the caller.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..orders.models import Order
from ..orders.enums import OrderStatus
from ..ledger_entries.service import LedgerEntryService
from ..positions.service import PositionAtomService
from .models import Trade
from .repository import TradeRepository
from .schemas import TradeCreate


class TradeNotFoundError(Exception):
    def __init__(self, trade_id: UUID):
        self.trade_id = trade_id
        super().__init__(f"Trade {trade_id} not found")


class OrderReferenceError(Exception):
    def __init__(self, order_id: UUID):
        self.order_id = order_id
        super().__init__(f"Referenced order {order_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class OrderNotExecutableError(Exception):
    def __init__(self, order_id: UUID, status: str):
        super().__init__(f"Order {order_id} is in status '{status}', not executable")


class TradeService:

    def __init__(self) -> None:
        self._repo = TradeRepository()
        self._ledger_service = LedgerEntryService()
        self._position_service = PositionAtomService()

    def record_trade(
        self,
        db: Session,
        payload: TradeCreate,
        execution_instruction_id: Optional[UUID] = None,
    ) -> Trade:
        """Record an executed trade, update order status, derive position.

        Sequence:
        1. Validate and persist the trade (immutable)
        2. Update order status if needed
        3. Call PositionService.apply_trade(trade) to update position state
        """
        order = db.query(Order).filter(Order.id == payload.order_id).first()
        if order is None:
            raise OrderReferenceError(payload.order_id)

        allowed_statuses = {OrderStatus.ACCEPTED.value, OrderStatus.EXECUTING.value, OrderStatus.PARTIALLY_FILLED.value}
        if order.status not in allowed_statuses:
            raise OrderNotExecutableError(payload.order_id, order.status)

        instrument = db.query(Instrument).filter(Instrument.id == payload.instrument_id).first()
        if instrument is None:
            raise InstrumentReferenceError(payload.instrument_id)

        gross_amount = payload.quantity * payload.price
        if payload.side == "buy":
            net_amount = gross_amount + payload.fee_amount
        else:
            net_amount = gross_amount - payload.fee_amount

        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        data["gross_amount"] = gross_amount
        data["net_amount"] = net_amount

        resolved_exec_id = execution_instruction_id or data.get("execution_instruction_id")
        data["execution_instruction_id"] = resolved_exec_id

        trade = self._repo.create(db, data=data)

        if order.status == OrderStatus.ACCEPTED.value:
            order.status = OrderStatus.EXECUTING.value
            db.flush()

        self._position_service.apply_trade(db, trade)

        return trade

    def get_trade(self, db: Session, trade_id: UUID) -> Trade:
        trade = self._repo.get_by_id(db, trade_id)
        if trade is None:
            raise TradeNotFoundError(trade_id)
        return trade

    def list_trades(
        self,
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        instrument_id: Optional[UUID] = None,
        side: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Trade], int]:
        return self._repo.list(
            db, order_id=order_id, instrument_id=instrument_id,
            side=side, skip=skip, limit=limit,
        )
