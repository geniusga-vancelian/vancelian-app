"""Tests for Portfolio Engine — Trades module."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.trades.models import Trade
from services.portfolio_engine.trades.repository import TradeRepository
from services.portfolio_engine.trades.service import (
    InstrumentReferenceError,
    OrderNotExecutableError,
    OrderReferenceError,
    TradeNotFoundError,
    TradeService,
)
from services.portfolio_engine.trades.schemas import TradeCreate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    return make_linked_client(db, email=f"trade-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")


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
        name="Trade Test PF", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def order_accepted(db: Session, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument) -> Order:
    o = Order(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id, order_type="market", side="buy",
        quantity=Decimal("0.5"), currency="EUR", status="accepted", metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def order_pending(db: Session, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument) -> Order:
    o = Order(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id, order_type="market", side="buy",
        quantity=Decimal("1"), currency="EUR", status="pending", metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def service() -> TradeService:
    return TradeService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestTradeRepository:

    def test_create(self, db: Session, order_accepted: Order, instrument_btc: Instrument):
        t = TradeRepository.create(db, data={
            "order_id": order_accepted.id,
            "instrument_id": instrument_btc.id,
            "side": "buy",
            "quantity": Decimal("0.25"),
            "price": Decimal("68000"),
            "gross_amount": Decimal("17000"),
            "fee_amount": Decimal("15"),
            "net_amount": Decimal("17015"),
            "currency": "EUR",
            "executed_at": datetime.now(timezone.utc),
            "metadata_": {},
        })
        assert t.id is not None
        assert t.gross_amount == Decimal("17000")

    def test_get_by_id(self, db: Session, order_accepted: Order, instrument_btc: Instrument):
        t = TradeRepository.create(db, data={
            "order_id": order_accepted.id,
            "instrument_id": instrument_btc.id,
            "side": "buy",
            "quantity": Decimal("0.1"),
            "price": Decimal("70000"),
            "gross_amount": Decimal("7000"),
            "fee_amount": Decimal("10"),
            "net_amount": Decimal("7010"),
            "currency": "EUR",
            "executed_at": datetime.now(timezone.utc),
            "metadata_": {},
        })
        found = TradeRepository.get_by_id(db, t.id)
        assert found is not None
        assert found.side == "buy"

    def test_get_by_id_not_found(self, db: Session):
        assert TradeRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_order(self, db: Session, order_accepted: Order, instrument_btc: Instrument):
        for i in range(3):
            TradeRepository.create(db, data={
                "order_id": order_accepted.id,
                "instrument_id": instrument_btc.id,
                "side": "buy",
                "quantity": Decimal("0.1"),
                "price": Decimal("68000"),
                "gross_amount": Decimal("6800"),
                "fee_amount": Decimal("5"),
                "net_amount": Decimal("6805"),
                "currency": "EUR",
                "executed_at": datetime.now(timezone.utc),
                "metadata_": {},
            })
        items, total = TradeRepository.list(db, order_id=order_accepted.id)
        assert total == 3


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestTradeService:

    def test_record_trade_buy(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.25"),
            price=Decimal("68000"),
            fee_amount=Decimal("15"),
            currency="EUR",
            counterparty="binance",
            executed_at=datetime.now(timezone.utc),
        )
        trade = service.record_trade(db, payload)
        assert trade.gross_amount == Decimal("0.25") * Decimal("68000")
        assert trade.net_amount == trade.gross_amount + Decimal("15")
        assert trade.counterparty == "binance"

    def test_record_trade_sell(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        buy_payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("68000"),
            fee_amount=Decimal("0"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        service.record_trade(db, buy_payload)

        order_accepted.side = "sell"
        order_accepted.status = "executing"
        db.flush()

        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="sell",
            quantity=Decimal("0.5"),
            price=Decimal("70000"),
            fee_amount=Decimal("20"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        trade = service.record_trade(db, payload)
        assert trade.gross_amount == Decimal("0.5") * Decimal("70000")
        assert trade.net_amount == trade.gross_amount - Decimal("20")

    def test_record_trade_transitions_order_to_executing(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        assert order_accepted.status == "accepted"
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        service.record_trade(db, payload)
        db.refresh(order_accepted)
        assert order_accepted.status == "executing"

    def test_record_trade_order_not_found(self, db: Session, service: TradeService, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=uuid.uuid4(),
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(OrderReferenceError):
            service.record_trade(db, payload)

    def test_record_trade_order_not_executable(self, db: Session, service: TradeService, order_pending: Order, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=order_pending.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(OrderNotExecutableError):
            service.record_trade(db, payload)

    def test_record_trade_instrument_not_found(self, db: Session, service: TradeService, order_accepted: Order):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=uuid.uuid4(),
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(InstrumentReferenceError):
            service.record_trade(db, payload)

    def test_record_trade_with_external_id(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            counterparty="binance",
            external_trade_id="binance-12345",
            executed_at=datetime.now(timezone.utc),
        )
        trade = service.record_trade(db, payload)
        assert trade.external_trade_id == "binance-12345"

    def test_get_trade(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        trade = service.record_trade(db, payload)
        found = service.get_trade(db, trade.id)
        assert found.id == trade.id

    def test_get_trade_not_found(self, db: Session, service: TradeService):
        with pytest.raises(TradeNotFoundError):
            service.get_trade(db, uuid.uuid4())

    def test_list_trades(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        service.record_trade(db, payload)
        items, total = service.list_trades(db, order_id=order_accepted.id)
        assert total >= 1

    def test_multiple_trades_per_order(self, db: Session, service: TradeService, order_accepted: Order, instrument_btc: Instrument):
        for i in range(3):
            payload = TradeCreate(
                order_id=order_accepted.id,
                instrument_id=instrument_btc.id,
                side="buy",
                quantity=Decimal("0.1"),
                price=Decimal(str(68000 + i * 100)),
                currency="EUR",
                executed_at=datetime.now(timezone.utc),
            )
            service.record_trade(db, payload)
        items, total = service.list_trades(db, order_id=order_accepted.id)
        assert total == 3
