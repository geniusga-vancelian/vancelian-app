"""Service layer for Execution module (Portfolio Engine — execution layer).

ExecutionInstruction is an operational layer between Order and Trade.
It does NOT write ledger entries. It does NOT settle assets.
Settlement remains the only writer of ledger entries.

The standard flow is:
    Order → ExecutionInstruction → (process_fill) → Trade
    Trade → SettlementInstruction → LedgerEntry (handled separately)
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..orders.models import Order
from ..trades.schemas import TradeCreate
from ..trades.service import TradeService
from .enums import (
    ExecutionStatus,
    ExecutionType,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
)
from .models import ExecutionInstruction
from .repository import ExecutionRepository
from .schemas import ExecutionCreate, FillReport


class ExecutionNotFoundError(Exception):
    def __init__(self, execution_id: UUID):
        self.execution_id = execution_id
        super().__init__(f"ExecutionInstruction {execution_id} not found")


class InvalidExecutionTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Cannot transition from '{current}' to '{target}'")


class OrderReferenceError(Exception):
    def __init__(self, order_id: UUID):
        super().__init__(f"Referenced order {order_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class ParentExecutionReferenceError(Exception):
    def __init__(self, parent_id: UUID):
        super().__init__(f"Referenced parent execution {parent_id} does not exist")


class ParentExecutionNotTerminalError(Exception):
    def __init__(self, parent_id: UUID, status: str):
        super().__init__(
            f"Parent execution {parent_id} is in non-terminal status '{status}'; "
            f"retries should reference terminal executions"
        )


class InstrumentRequiredError(Exception):
    def __init__(self, execution_type: str):
        super().__init__(
            f"instrument_id is required for execution_type '{execution_type}'"
        )


class SideRequiredError(Exception):
    def __init__(self, execution_type: str):
        super().__init__(
            f"side is required for execution_type '{execution_type}'"
        )


class QuantityOrAmountRequiredError(Exception):
    def __init__(self):
        super().__init__("At least one of quantity or amount must be provided")


class PriceLimitRequiredError(Exception):
    def __init__(self):
        super().__init__("price_limit is required for limit execution_type")


class ExecutionNotFillableError(Exception):
    def __init__(self, execution_id: UUID, status: str):
        super().__init__(
            f"ExecutionInstruction {execution_id} in status '{status}' cannot receive fills"
        )


class ExecutionService:

    def __init__(self) -> None:
        self._repo = ExecutionRepository()
        self._trade_service = TradeService()

    @staticmethod
    def _validate_order_exists(db: Session, order_id: UUID) -> Order:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise OrderReferenceError(order_id)
        return order

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
            raise InstrumentReferenceError(instrument_id)

    def _validate_parent(self, db: Session, parent_id: UUID) -> None:
        parent = self._repo.get_by_id(db, parent_id)
        if parent is None:
            raise ParentExecutionReferenceError(parent_id)
        if ExecutionStatus(parent.status) not in TERMINAL_STATUSES:
            raise ParentExecutionNotTerminalError(parent_id, parent.status)

    @staticmethod
    def _validate_business_rules(payload: ExecutionCreate) -> None:
        market_limit = {ExecutionType.MARKET, ExecutionType.LIMIT}

        if payload.execution_type in market_limit and payload.instrument_id is None:
            raise InstrumentRequiredError(payload.execution_type.value)

        if payload.execution_type in market_limit and payload.side is None:
            raise SideRequiredError(payload.execution_type.value)

        if payload.quantity is None and payload.amount is None:
            raise QuantityOrAmountRequiredError()

        if payload.execution_type == ExecutionType.LIMIT and payload.price_limit is None:
            raise PriceLimitRequiredError()

    def create_execution(
        self, db: Session, payload: ExecutionCreate
    ) -> ExecutionInstruction:
        self._validate_order_exists(db, payload.order_id)
        self._validate_business_rules(payload)

        if payload.instrument_id is not None:
            self._validate_instrument_exists(db, payload.instrument_id)

        if payload.parent_execution_id is not None:
            self._validate_parent(db, payload.parent_execution_id)

        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        data["venue"] = data["venue"].value if hasattr(data["venue"], "value") else data["venue"]
        data["execution_type"] = data["execution_type"].value if hasattr(data["execution_type"], "value") else data["execution_type"]
        return self._repo.create(db, data=data)

    def get_execution(
        self, db: Session, execution_id: UUID
    ) -> ExecutionInstruction:
        instruction = self._repo.get_by_id(db, execution_id)
        if instruction is None:
            raise ExecutionNotFoundError(execution_id)
        return instruction

    def list_executions(
        self,
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        venue: Optional[str] = None,
        execution_type: Optional[str] = None,
        status: Optional[str] = None,
        instrument_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ExecutionInstruction], int]:
        return self._repo.list(
            db,
            order_id=order_id,
            venue=venue,
            execution_type=execution_type,
            status=status,
            instrument_id=instrument_id,
            skip=skip,
            limit=limit,
        )

    def _transition(
        self,
        db: Session,
        execution_id: UUID,
        target: ExecutionStatus,
        **kwargs,
    ) -> ExecutionInstruction:
        instruction = self.get_execution(db, execution_id)
        current = ExecutionStatus(instruction.status)
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise InvalidExecutionTransitionError(instruction.status, target.value)
        return self._repo.update_fields(
            db, instruction, status=target.value, **kwargs
        )

    def mark_sent(
        self,
        db: Session,
        execution_id: UUID,
        *,
        venue_order_id: Optional[str] = None,
    ) -> ExecutionInstruction:
        kwargs: dict = {"sent_at": datetime.now(timezone.utc)}
        if venue_order_id is not None:
            kwargs["venue_order_id"] = venue_order_id
        return self._transition(db, execution_id, ExecutionStatus.SENT, **kwargs)

    def mark_acknowledged(
        self,
        db: Session,
        execution_id: UUID,
        *,
        venue_order_id: Optional[str] = None,
    ) -> ExecutionInstruction:
        kwargs: dict = {"acknowledged_at": datetime.now(timezone.utc)}
        if venue_order_id is not None:
            kwargs["venue_order_id"] = venue_order_id
        return self._transition(
            db, execution_id, ExecutionStatus.ACKNOWLEDGED, **kwargs
        )

    def reject(
        self, db: Session, execution_id: UUID, reason: str
    ) -> ExecutionInstruction:
        return self._transition(
            db,
            execution_id,
            ExecutionStatus.REJECTED,
            rejected_at=datetime.now(timezone.utc),
            failure_reason=reason,
        )

    def expire(self, db: Session, execution_id: UUID) -> ExecutionInstruction:
        return self._transition(
            db,
            execution_id,
            ExecutionStatus.EXPIRED,
            expired_at=datetime.now(timezone.utc),
        )

    def cancel(self, db: Session, execution_id: UUID) -> ExecutionInstruction:
        return self._transition(
            db,
            execution_id,
            ExecutionStatus.CANCELLED,
            cancelled_at=datetime.now(timezone.utc),
        )

    def fail(
        self, db: Session, execution_id: UUID, reason: str
    ) -> ExecutionInstruction:
        return self._transition(
            db,
            execution_id,
            ExecutionStatus.FAILED,
            failure_reason=reason,
        )

    def process_fill(
        self,
        db: Session,
        execution_id: UUID,
        fill: FillReport,
    ) -> "tuple[ExecutionInstruction, object]":
        """Process a fill event: create a Trade and update execution progress.

        This method does NOT create settlements and does NOT write ledger entries.
        Settlement creation remains the caller's responsibility.

        Returns:
            Tuple of (updated ExecutionInstruction, created Trade).
        """
        instruction = self.get_execution(db, execution_id)
        fillable = {
            ExecutionStatus.ACKNOWLEDGED.value,
            ExecutionStatus.PARTIALLY_FILLED.value,
        }
        if instruction.status not in fillable:
            raise ExecutionNotFillableError(execution_id, instruction.status)

        trade_payload = TradeCreate(
            order_id=instruction.order_id,
            instrument_id=instruction.instrument_id,
            side=instruction.side,
            quantity=fill.quantity,
            price=fill.price,
            fee_amount=fill.fee_amount,
            currency=fill.currency,
            counterparty=fill.counterparty,
            external_trade_id=fill.external_trade_id,
            executed_at=fill.executed_at,
        )
        trade = self._trade_service.record_trade(
            db, trade_payload, execution_instruction_id=instruction.id
        )

        prev_filled = Decimal(str(instruction.filled_quantity or 0))
        new_filled = prev_filled + fill.quantity

        if prev_filled == 0:
            new_avg = fill.price
        else:
            prev_avg = Decimal(str(instruction.average_fill_price or 0))
            new_avg = (
                (prev_avg * prev_filled + fill.price * fill.quantity) / new_filled
            )

        target_qty = instruction.quantity
        if target_qty is not None and new_filled >= Decimal(str(target_qty)):
            new_status = ExecutionStatus.FILLED
            extra = {"executed_at": datetime.now(timezone.utc)}
        else:
            new_status = ExecutionStatus.PARTIALLY_FILLED
            extra = {}

        self._repo.update_fields(
            db,
            instruction,
            status=new_status.value,
            filled_quantity=new_filled,
            average_fill_price=new_avg,
            **extra,
        )

        return instruction, trade
