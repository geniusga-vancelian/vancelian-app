"""Tests for Portfolio Engine — Position Engine (apply_trade)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.positions.repository import PositionAtomRepository
from services.portfolio_engine.positions.service import (
    InsufficientPositionError,
    NoOpenPositionError,
    PositionAtomService,
)
from services.portfolio_engine.trades.models import Trade
from services.portfolio_engine.trades.service import TradeService
from services.portfolio_engine.trades.schemas import TradeCreate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    c = Client(
        id=uuid.uuid4(),
        email=f"pos-{uuid.uuid4().hex[:8]}@test.com",
        status="active",
        kyc_status="approved",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol=f"BTC-{uuid.uuid4().hex[:6]}",
        name="Bitcoin",
        asset_type="crypto",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code=f"BTC-SPOT-{uuid.uuid4().hex[:6]}",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session, client_active: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=client_active.id,
        portfolio_type="bundle_portfolio",
        name="Position Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def order_accepted(
    db: Session, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument
) -> Order:
    o = Order(
        id=uuid.uuid4(),
        client_id=client_active.id,
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        order_type="market",
        side="buy",
        quantity=Decimal("10"),
        currency="EUR",
        status="accepted",
        metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def position_service() -> PositionAtomService:
    return PositionAtomService()


@pytest.fixture
def trade_service() -> TradeService:
    return TradeService()


def _make_trade_create(order: Order, instrument: Instrument, side: str, qty, price) -> TradeCreate:
    return TradeCreate(
        order_id=order.id,
        instrument_id=instrument.id,
        side=side,
        quantity=Decimal(str(qty)),
        price=Decimal(str(price)),
        fee_amount=Decimal("0"),
        currency="EUR",
        executed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Repository — find_open
# ---------------------------------------------------------------------------

class TestPositionAtomRepositoryFindOpen:

    def test_find_open_returns_none_when_empty(self, db: Session, portfolio: Portfolio, instrument_btc: Instrument):
        result = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert result is None

    def test_find_open_returns_open_position(self, db: Session, portfolio: Portfolio, instrument_btc: Instrument):
        PositionAtomRepository.create(db, data={
            "portfolio_id": portfolio.id,
            "instrument_id": instrument_btc.id,
            "position_type": "spot",
            "status": "open",
            "quantity": Decimal("1"),
            "available_quantity": Decimal("1"),
            "metadata_": {},
        })
        result = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert result is not None
        assert result.status == "open"

    def test_find_open_ignores_closed(self, db: Session, portfolio: Portfolio, instrument_btc: Instrument):
        PositionAtomRepository.create(db, data={
            "portfolio_id": portfolio.id,
            "instrument_id": instrument_btc.id,
            "position_type": "spot",
            "status": "closed",
            "quantity": Decimal("0"),
            "available_quantity": Decimal("0"),
            "metadata_": {},
        })
        result = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert result is None


# ---------------------------------------------------------------------------
# Position Engine — apply_trade via TradeService integration
# ---------------------------------------------------------------------------

class TestPositionEngineApplyTrade:

    def test_first_buy_creates_position(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        payload = _make_trade_create(order_accepted, instrument_btc, "buy", "0.5", "68000")
        trade = trade_service.record_trade(db, payload)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position is not None
        assert position.quantity == Decimal("0.5")
        assert position.average_entry_price == Decimal("68000")
        assert position.status == "open"
        assert position.realized_pnl == Decimal("0")

    def test_second_buy_increases_position(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        payload1 = _make_trade_create(order_accepted, instrument_btc, "buy", "0.5", "68000")
        trade_service.record_trade(db, payload1)

        payload2 = _make_trade_create(order_accepted, instrument_btc, "buy", "0.3", "70000")
        trade_service.record_trade(db, payload2)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position.quantity == Decimal("0.8")
        expected_avg = (Decimal("0.5") * Decimal("68000") + Decimal("0.3") * Decimal("70000")) / Decimal("0.8")
        assert position.average_entry_price == expected_avg

    def test_partial_sell_reduces_position(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        buy_payload = _make_trade_create(order_accepted, instrument_btc, "buy", "1", "50000")
        trade_service.record_trade(db, buy_payload)

        order_accepted.side = "sell"
        order_accepted.status = "executing"
        db.flush()

        sell_payload = _make_trade_create(order_accepted, instrument_btc, "sell", "0.3", "60000")
        trade_service.record_trade(db, sell_payload)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position.quantity == Decimal("0.7")
        assert position.status == "open"

        expected_pnl = Decimal("0.3") * (Decimal("60000") - Decimal("50000"))
        assert position.realized_pnl == expected_pnl

    def test_full_sell_closes_position(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        buy_payload = _make_trade_create(order_accepted, instrument_btc, "buy", "1", "50000")
        trade_service.record_trade(db, buy_payload)

        order_accepted.side = "sell"
        order_accepted.status = "executing"
        db.flush()

        sell_payload = _make_trade_create(order_accepted, instrument_btc, "sell", "1", "60000")
        trade_service.record_trade(db, sell_payload)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position is None

        closed = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == instrument_btc.id,
            PositionAtom.status == "closed",
        ).first()
        assert closed is not None
        assert closed.quantity == Decimal("0")
        assert closed.realized_pnl == Decimal("1") * (Decimal("60000") - Decimal("50000"))
        assert closed.closed_at is not None

    def test_sell_greater_than_position_rejected(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        buy_payload = _make_trade_create(order_accepted, instrument_btc, "buy", "0.5", "68000")
        trade_service.record_trade(db, buy_payload)

        order_accepted.side = "sell"
        order_accepted.status = "executing"
        db.flush()

        sell_payload = _make_trade_create(order_accepted, instrument_btc, "sell", "0.6", "70000")
        with pytest.raises(InsufficientPositionError):
            trade_service.record_trade(db, sell_payload)

    def test_sell_without_position_rejected(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument,
    ):
        order_accepted.side = "sell"
        order_accepted.status = "executing"
        db.flush()

        sell_payload = _make_trade_create(order_accepted, instrument_btc, "sell", "0.1", "68000")
        with pytest.raises(NoOpenPositionError):
            trade_service.record_trade(db, sell_payload)

    def test_realized_pnl_correct_on_multiple_sells(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        buy_payload = _make_trade_create(order_accepted, instrument_btc, "buy", "1", "50000")
        trade_service.record_trade(db, buy_payload)

        order_accepted.status = "executing"
        db.flush()

        sell_1 = _make_trade_create(order_accepted, instrument_btc, "sell", "0.4", "60000")
        trade_service.record_trade(db, sell_1)

        sell_2 = _make_trade_create(order_accepted, instrument_btc, "sell", "0.3", "55000")
        trade_service.record_trade(db, sell_2)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position.quantity == Decimal("0.3")

        pnl_1 = Decimal("0.4") * (Decimal("60000") - Decimal("50000"))
        pnl_2 = Decimal("0.3") * (Decimal("55000") - Decimal("50000"))
        assert position.realized_pnl == pnl_1 + pnl_2

    def test_fees_do_not_affect_position_quantity(
        self, db: Session, trade_service: TradeService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.5"),
            price=Decimal("68000"),
            fee_amount=Decimal("51"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        trade_service.record_trade(db, payload)

        position = PositionAtomRepository.find_open(db, portfolio.id, instrument_btc.id)
        assert position.quantity == Decimal("0.5")
        assert position.average_entry_price == Decimal("68000")


# ---------------------------------------------------------------------------
# Direct PositionService.apply_trade tests
# ---------------------------------------------------------------------------

class TestPositionServiceApplyTradeDirect:

    def test_apply_buy_creates_position(
        self, db: Session, position_service: PositionAtomService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        trade = Trade(
            id=uuid.uuid4(),
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.25"),
            price=Decimal("65000"),
            gross_amount=Decimal("16250"),
            fee_amount=Decimal("0"),
            net_amount=Decimal("16250"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
            metadata_={},
        )
        db.add(trade)
        db.flush()

        position = position_service.apply_trade(db, trade)
        assert position.portfolio_id == portfolio.id
        assert position.instrument_id == instrument_btc.id
        assert position.quantity == Decimal("0.25")
        assert position.average_entry_price == Decimal("65000")
        assert position.status == "open"

    def test_apply_sell_reduces_position(
        self, db: Session, position_service: PositionAtomService,
        order_accepted: Order, instrument_btc: Instrument, portfolio: Portfolio,
    ):
        PositionAtomRepository.create(db, data={
            "portfolio_id": portfolio.id,
            "instrument_id": instrument_btc.id,
            "position_type": "spot",
            "status": "open",
            "quantity": Decimal("1"),
            "available_quantity": Decimal("1"),
            "average_entry_price": Decimal("50000"),
            "realized_pnl": Decimal("0"),
            "metadata_": {},
        })

        trade = Trade(
            id=uuid.uuid4(),
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="sell",
            quantity=Decimal("0.5"),
            price=Decimal("60000"),
            gross_amount=Decimal("30000"),
            fee_amount=Decimal("0"),
            net_amount=Decimal("30000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
            metadata_={},
        )
        db.add(trade)
        db.flush()

        position = position_service.apply_trade(db, trade)
        assert position.quantity == Decimal("0.5")
        assert position.realized_pnl == Decimal("0.5") * (Decimal("60000") - Decimal("50000"))
