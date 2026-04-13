"""Tests for Portfolio Engine — Orders module."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.orders.enums import OrderStatus, VALID_TRANSITIONS
from services.portfolio_engine.orders.repository import OrderRepository
from services.portfolio_engine.orders.service import (
    ClientReferenceError,
    InstrumentReferenceError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    OrderService,
    PortfolioReferenceError,
)
from services.portfolio_engine.orders.schemas import OrderCreate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    return make_linked_client(db, email=f"order-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol=f"BTC-{uuid.uuid4().hex[:6]}", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(id=uuid.uuid4(), asset_id=asset_btc.id, code=f"BTC-SPOT-{uuid.uuid4().hex[:6]}", name="BTC Spot", instrument_type="spot", metadata_={})
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session, client_active: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_type="bundle_portfolio",
        name="Test PF", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def order_pending(db: Session, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument) -> Order:
    o = Order(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id, order_type="market", side="buy",
        quantity=Decimal("0.5"), currency="EUR", status="pending", metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def service() -> OrderService:
    return OrderService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestOrderRepository:

    def test_create(self, db: Session, client_active: Client, portfolio: Portfolio):
        o = OrderRepository.create(db, data={
            "client_id": client_active.id,
            "portfolio_id": portfolio.id,
            "order_type": "deposit",
            "amount": Decimal("5000"),
            "currency": "EUR",
            "status": "pending",
            "metadata_": {},
        })
        assert o.id is not None
        assert o.order_type == "deposit"
        assert o.side is None

    def test_get_by_id(self, db: Session, order_pending: Order):
        found = OrderRepository.get_by_id(db, order_pending.id)
        assert found is not None
        assert found.order_type == "market"

    def test_get_by_id_not_found(self, db: Session):
        assert OrderRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, order_pending: Order):
        items, total = OrderRepository.list(db)
        assert total >= 1

    def test_list_filter_by_client(self, db: Session, order_pending: Order, client_active: Client):
        items, total = OrderRepository.list(db, client_id=client_active.id)
        assert total >= 1
        assert all(o.client_id == client_active.id for o in items)

    def test_list_filter_by_status(self, db: Session, order_pending: Order):
        items, total = OrderRepository.list(db, status="pending")
        assert total >= 1
        assert all(o.status == "pending" for o in items)

    def test_update_status(self, db: Session, order_pending: Order):
        OrderRepository.update_status(db, order_pending, status="accepted")
        db.flush()
        refreshed = OrderRepository.get_by_id(db, order_pending.id)
        assert refreshed.status == "accepted"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestOrderService:

    def test_create_order_market(self, db: Session, service: OrderService, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument):
        payload = OrderCreate(
            client_id=client_active.id, portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id, order_type="market", side="buy",
            quantity=Decimal("0.1"), currency="EUR",
        )
        order = service.create_order(db, payload)
        assert order.order_type == "market"
        assert order.side == "buy"
        assert order.status == "pending"

    def test_create_order_deposit_no_instrument(self, db: Session, service: OrderService, client_active: Client, portfolio: Portfolio):
        payload = OrderCreate(
            client_id=client_active.id, portfolio_id=portfolio.id,
            order_type="deposit", amount=Decimal("10000"), currency="EUR",
        )
        order = service.create_order(db, payload)
        assert order.order_type == "deposit"
        assert order.instrument_id is None
        assert order.side is None

    def test_create_order_invalid_client(self, db: Session, service: OrderService, portfolio: Portfolio):
        payload = OrderCreate(
            client_id=uuid.uuid4(), portfolio_id=portfolio.id,
            order_type="deposit", amount=Decimal("100"), currency="EUR",
        )
        with pytest.raises(ClientReferenceError):
            service.create_order(db, payload)

    def test_create_order_invalid_portfolio(self, db: Session, service: OrderService, client_active: Client):
        payload = OrderCreate(
            client_id=client_active.id, portfolio_id=uuid.uuid4(),
            order_type="deposit", amount=Decimal("100"), currency="EUR",
        )
        with pytest.raises(PortfolioReferenceError):
            service.create_order(db, payload)

    def test_create_order_invalid_instrument(self, db: Session, service: OrderService, client_active: Client, portfolio: Portfolio):
        payload = OrderCreate(
            client_id=client_active.id, portfolio_id=portfolio.id,
            instrument_id=uuid.uuid4(), order_type="market", side="buy",
            quantity=Decimal("1"), currency="EUR",
        )
        with pytest.raises(InstrumentReferenceError):
            service.create_order(db, payload)

    def test_get_order(self, db: Session, service: OrderService, order_pending: Order):
        found = service.get_order(db, order_pending.id)
        assert found.id == order_pending.id

    def test_get_order_not_found(self, db: Session, service: OrderService):
        with pytest.raises(OrderNotFoundError):
            service.get_order(db, uuid.uuid4())

    def test_accept_order(self, db: Session, service: OrderService, order_pending: Order):
        accepted = service.accept_order(db, order_pending.id)
        assert accepted.status == "accepted"

    def test_reject_order(self, db: Session, service: OrderService, order_pending: Order):
        rejected = service.reject_order(db, order_pending.id, "Insufficient funds")
        assert rejected.status == "rejected"
        assert rejected.rejection_reason == "Insufficient funds"

    def test_cancel_from_accepted(self, db: Session, service: OrderService, order_pending: Order):
        service.accept_order(db, order_pending.id)
        cancelled = service.cancel_order(db, order_pending.id)
        assert cancelled.status == "cancelled"

    def test_full_lifecycle_pending_to_completed(self, db: Session, service: OrderService, order_pending: Order):
        service.accept_order(db, order_pending.id)
        service.mark_executing(db, order_pending.id)
        completed = service.mark_completed(db, order_pending.id)
        assert completed.status == "completed"

    def test_partial_fill_then_complete(self, db: Session, service: OrderService, order_pending: Order):
        service.accept_order(db, order_pending.id)
        service.mark_executing(db, order_pending.id)
        service.mark_partially_filled(db, order_pending.id)
        completed = service.mark_completed(db, order_pending.id)
        assert completed.status == "completed"

    def test_invalid_transition_pending_to_completed(self, db: Session, service: OrderService, order_pending: Order):
        with pytest.raises(InvalidStatusTransitionError):
            service.mark_completed(db, order_pending.id)

    def test_invalid_transition_rejected_to_accepted(self, db: Session, service: OrderService, order_pending: Order):
        service.reject_order(db, order_pending.id, "Bad order")
        with pytest.raises(InvalidStatusTransitionError):
            service.accept_order(db, order_pending.id)

    def test_invalid_transition_completed_to_cancelled(self, db: Session, service: OrderService, order_pending: Order):
        service.accept_order(db, order_pending.id)
        service.mark_executing(db, order_pending.id)
        service.mark_completed(db, order_pending.id)
        with pytest.raises(InvalidStatusTransitionError):
            service.cancel_order(db, order_pending.id)

    def test_list_orders(self, db: Session, service: OrderService, order_pending: Order):
        items, total = service.list_orders(db)
        assert total >= 1
