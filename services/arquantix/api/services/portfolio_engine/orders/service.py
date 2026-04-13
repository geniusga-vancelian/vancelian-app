"""Service layer for Orders module (Portfolio Engine — transaction layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..clients.models import Client
from ..instruments.models import Instrument
from ..portfolios.models import Portfolio
from .enums import OrderStatus, VALID_TRANSITIONS
from .models import Order
from .repository import OrderRepository
from .schemas import OrderCreate


class OrderNotFoundError(Exception):
    def __init__(self, order_id: UUID):
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")


class ClientReferenceError(Exception):
    def __init__(self, client_id: UUID):
        self.client_id = client_id
        super().__init__(f"Referenced client {client_id} does not exist")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class InstrumentReferenceError(Exception):
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class InvalidStatusTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Cannot transition from '{current}' to '{target}'")


class OrderService:

    def __init__(self) -> None:
        self._repo = OrderRepository()

    @staticmethod
    def _validate_client_exists(db: Session, client_id: UUID) -> None:
        if db.query(Client).filter(Client.id == client_id).first() is None:
            raise ClientReferenceError(client_id)

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
            raise InstrumentReferenceError(instrument_id)

    def create_order(self, db: Session, payload: OrderCreate) -> Order:
        self._validate_client_exists(db, payload.client_id)
        self._validate_portfolio_exists(db, payload.portfolio_id)
        if payload.instrument_id is not None:
            self._validate_instrument_exists(db, payload.instrument_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_order(self, db: Session, order_id: UUID) -> Order:
        order = self._repo.get_by_id(db, order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def list_orders(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        portfolio_id: Optional[UUID] = None,
        order_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Order], int]:
        return self._repo.list(
            db, client_id=client_id, portfolio_id=portfolio_id,
            order_type=order_type, status=status, skip=skip, limit=limit,
        )

    def _transition_status(self, db: Session, order_id: UUID, target: OrderStatus, rejection_reason: Optional[str] = None) -> Order:
        order = self.get_order(db, order_id)
        current = OrderStatus(order.status)
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise InvalidStatusTransitionError(order.status, target.value)
        return self._repo.update_status(db, order, status=target.value, rejection_reason=rejection_reason)

    def accept_order(self, db: Session, order_id: UUID) -> Order:
        return self._transition_status(db, order_id, OrderStatus.ACCEPTED)

    def reject_order(self, db: Session, order_id: UUID, reason: str) -> Order:
        return self._transition_status(db, order_id, OrderStatus.REJECTED, rejection_reason=reason)

    def cancel_order(self, db: Session, order_id: UUID) -> Order:
        return self._transition_status(db, order_id, OrderStatus.CANCELLED)

    def mark_executing(self, db: Session, order_id: UUID) -> Order:
        return self._transition_status(db, order_id, OrderStatus.EXECUTING)

    def mark_completed(self, db: Session, order_id: UUID) -> Order:
        return self._transition_status(db, order_id, OrderStatus.COMPLETED)

    def mark_partially_filled(self, db: Session, order_id: UUID) -> Order:
        return self._transition_status(db, order_id, OrderStatus.PARTIALLY_FILLED)
