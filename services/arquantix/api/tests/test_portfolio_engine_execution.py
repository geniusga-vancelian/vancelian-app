"""Tests for Portfolio Engine — Execution module (Phase 3)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.execution.enums import (
    ExecutionStatus,
    ExecutionType,
    ExecutionVenue,
    TERMINAL_STATUSES,
)
from services.portfolio_engine.execution.models import ExecutionInstruction
from services.portfolio_engine.execution.repository import ExecutionRepository
from services.portfolio_engine.execution.schemas import ExecutionCreate, FillReport
from services.portfolio_engine.execution.service import (
    ExecutionNotFillableError,
    ExecutionNotFoundError,
    ExecutionService,
    InstrumentRequiredError,
    InvalidExecutionTransitionError,
    OrderReferenceError,
    ParentExecutionNotTerminalError,
    ParentExecutionReferenceError,
    PriceLimitRequiredError,
    QuantityOrAmountRequiredError,
    SideRequiredError,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.trades.models import Trade
from services.portfolio_engine.trades.schemas import TradeCreate
from services.portfolio_engine.trades.service import TradeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    return make_linked_client(db, email=f"exec-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")


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
        name="Exec Test PF",
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
        quantity=Decimal("1.0"),
        currency="EUR",
        status="accepted",
        metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def service() -> ExecutionService:
    return ExecutionService()


@pytest.fixture
def trade_service() -> TradeService:
    return TradeService()


def _make_market_create(order: Order, instrument: Instrument) -> ExecutionCreate:
    return ExecutionCreate(
        order_id=order.id,
        venue=ExecutionVenue.BINANCE,
        execution_type=ExecutionType.MARKET,
        instrument_id=instrument.id,
        side="buy",
        quantity=Decimal("1.0"),
        currency="EUR",
        requested_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Create happy path
# ---------------------------------------------------------------------------

class TestExecutionCreate:

    def test_create_market(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = _make_market_create(order_accepted, instrument_btc)
        inst = service.create_execution(db, payload)
        assert inst.id is not None
        assert inst.status == "pending"
        assert inst.venue == "binance"
        assert inst.execution_type == "market"
        assert inst.instrument_id == instrument_btc.id
        assert inst.side == "buy"

    def test_create_limit(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.LIMIT,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.5"),
            price_limit=Decimal("68000"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        inst = service.create_execution(db, payload)
        assert inst.execution_type == "limit"
        assert inst.price_limit == Decimal("68000")

    def test_create_internal(self, db: Session, service: ExecutionService, order_accepted):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.INTERNAL,
            execution_type=ExecutionType.INTERNAL,
            amount=Decimal("10000"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        inst = service.create_execution(db, payload)
        assert inst.instrument_id is None
        assert inst.side is None
        assert inst.amount == Decimal("10000")

    def test_create_manual(self, db: Session, service: ExecutionService, order_accepted):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.MANUAL,
            execution_type=ExecutionType.MANUAL,
            amount=Decimal("5000"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        inst = service.create_execution(db, payload)
        assert inst.venue == "manual"
        assert inst.execution_type == "manual"

    def test_get_execution(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = _make_market_create(order_accepted, instrument_btc)
        created = service.create_execution(db, payload)
        found = service.get_execution(db, created.id)
        assert found.id == created.id

    def test_get_execution_not_found(self, db: Session, service: ExecutionService):
        with pytest.raises(ExecutionNotFoundError):
            service.get_execution(db, uuid.uuid4())

    def test_list_executions(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        for _ in range(3):
            service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        items, total = service.list_executions(db, order_id=order_accepted.id)
        assert total == 3


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestExecutionValidation:

    def test_order_not_found(self, db: Session, service: ExecutionService, instrument_btc):
        payload = ExecutionCreate(
            order_id=uuid.uuid4(),
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(OrderReferenceError):
            service.create_execution(db, payload)

    def test_instrument_required_for_market(self, db: Session, service: ExecutionService, order_accepted):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            side="buy",
            quantity=Decimal("1"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(InstrumentRequiredError):
            service.create_execution(db, payload)

    def test_instrument_required_for_limit(self, db: Session, service: ExecutionService, order_accepted):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.LIMIT,
            side="buy",
            quantity=Decimal("1"),
            price_limit=Decimal("68000"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(InstrumentRequiredError):
            service.create_execution(db, payload)

    def test_side_required_for_market(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            quantity=Decimal("1"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(SideRequiredError):
            service.create_execution(db, payload)

    def test_quantity_or_amount_required(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            side="buy",
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(QuantityOrAmountRequiredError):
            service.create_execution(db, payload)

    def test_price_limit_required_for_limit(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.LIMIT,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(PriceLimitRequiredError):
            service.create_execution(db, payload)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

class TestExecutionTransitions:

    def test_pending_to_sent(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        updated = service.mark_sent(db, inst.id, venue_order_id="BN-123")
        assert updated.status == "sent"
        assert updated.sent_at is not None
        assert updated.venue_order_id == "BN-123"

    def test_sent_to_acknowledged(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        updated = service.mark_acknowledged(db, inst.id, venue_order_id="BN-456")
        assert updated.status == "acknowledged"
        assert updated.acknowledged_at is not None

    def test_acknowledged_to_filled(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)
        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68200"),
            currency="EUR",
            counterparty="binance",
            executed_at=datetime.now(timezone.utc),
        )
        updated, trade = service.process_fill(db, inst.id, fill)
        assert updated.status == "filled"
        assert updated.executed_at is not None
        assert updated.filled_quantity == Decimal("1.0")

    def test_reject_from_sent(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        updated = service.reject(db, inst.id, "Insufficient balance")
        assert updated.status == "rejected"
        assert updated.rejected_at is not None
        assert updated.failure_reason == "Insufficient balance"

    def test_expire_from_acknowledged(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)
        updated = service.expire(db, inst.id)
        assert updated.status == "expired"
        assert updated.expired_at is not None

    def test_cancel_from_pending(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        updated = service.cancel(db, inst.id)
        assert updated.status == "cancelled"
        assert updated.cancelled_at is not None

    def test_fail_from_pending(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        updated = service.fail(db, inst.id, "Network timeout")
        assert updated.status == "failed"
        assert updated.failure_reason == "Network timeout"

    def test_invalid_transition_pending_to_filled(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ExecutionNotFillableError):
            service.process_fill(db, inst.id, fill)

    def test_invalid_transition_filled_to_sent(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)
        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        service.process_fill(db, inst.id, fill)
        with pytest.raises(InvalidExecutionTransitionError):
            service.mark_sent(db, inst.id)

    def test_invalid_transition_rejected_to_anything(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.reject(db, inst.id, "rejected")
        with pytest.raises(InvalidExecutionTransitionError):
            service.mark_sent(db, inst.id)


# ---------------------------------------------------------------------------
# Terminal states
# ---------------------------------------------------------------------------

class TestTerminalStates:

    def test_all_terminals_reject_transitions(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        for status in TERMINAL_STATUSES:
            inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
            if status == ExecutionStatus.FILLED:
                service.mark_sent(db, inst.id)
                service.mark_acknowledged(db, inst.id)
                fill = FillReport(
                    quantity=Decimal("1.0"), price=Decimal("68000"),
                    currency="EUR", executed_at=datetime.now(timezone.utc),
                )
                service.process_fill(db, inst.id, fill)
            elif status == ExecutionStatus.REJECTED:
                service.mark_sent(db, inst.id)
                service.reject(db, inst.id, "test")
            elif status == ExecutionStatus.EXPIRED:
                service.mark_sent(db, inst.id)
                service.mark_acknowledged(db, inst.id)
                service.expire(db, inst.id)
            elif status == ExecutionStatus.CANCELLED:
                service.cancel(db, inst.id)
            elif status == ExecutionStatus.FAILED:
                service.fail(db, inst.id, "test")

            with pytest.raises(InvalidExecutionTransitionError):
                service.cancel(db, inst.id)


# ---------------------------------------------------------------------------
# Process fill
# ---------------------------------------------------------------------------

class TestProcessFill:

    def test_fill_creates_trade(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)

        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68200"),
            currency="EUR",
            counterparty="binance",
            external_trade_id="BN-T-001",
            executed_at=datetime.now(timezone.utc),
        )
        updated, trade = service.process_fill(db, inst.id, fill)

        assert trade.id is not None
        assert trade.order_id == order_accepted.id
        assert trade.instrument_id == instrument_btc.id
        assert trade.quantity == Decimal("1.0")
        assert trade.price == Decimal("68200")
        assert trade.counterparty == "binance"
        assert trade.external_trade_id == "BN-T-001"

    def test_fill_updates_filled_quantity(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)

        fill = FillReport(
            quantity=Decimal("0.5"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        updated, _ = service.process_fill(db, inst.id, fill)
        assert updated.filled_quantity == Decimal("0.5")
        assert updated.average_fill_price == Decimal("68000")
        assert updated.status == "partially_filled"

    def test_partial_then_final_fill(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)

        fill_1 = FillReport(
            quantity=Decimal("0.4"),
            price=Decimal("67900"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        updated, trade_1 = service.process_fill(db, inst.id, fill_1)
        assert updated.status == "partially_filled"
        assert updated.filled_quantity == Decimal("0.4")

        fill_2 = FillReport(
            quantity=Decimal("0.6"),
            price=Decimal("68100"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        updated, trade_2 = service.process_fill(db, inst.id, fill_2)
        assert updated.status == "filled"
        assert updated.filled_quantity == Decimal("1.0")
        assert updated.executed_at is not None

        expected_avg = (
            Decimal("67900") * Decimal("0.4") + Decimal("68100") * Decimal("0.6")
        ) / Decimal("1.0")
        assert updated.average_fill_price == expected_avg

        assert trade_1.id != trade_2.id
        assert trade_1.order_id == trade_2.order_id == order_accepted.id

    def test_fill_not_fillable_from_pending(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ExecutionNotFillableError):
            service.process_fill(db, inst.id, fill)

    def test_fill_not_fillable_from_sent(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ExecutionNotFillableError):
            service.process_fill(db, inst.id, fill)


# ---------------------------------------------------------------------------
# Trade integration — execution_instruction_id
# ---------------------------------------------------------------------------

class TestTradeExecutionLink:

    def test_fill_writes_execution_instruction_id_on_trade(
        self, db: Session, service: ExecutionService, order_accepted, instrument_btc
    ):
        inst = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, inst.id)
        service.mark_acknowledged(db, inst.id)

        fill = FillReport(
            quantity=Decimal("1.0"),
            price=Decimal("68200"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        _, trade = service.process_fill(db, inst.id, fill)
        assert trade.execution_instruction_id == inst.id

    def test_legacy_trade_creation_without_execution(
        self, db: Session, trade_service: TradeService, order_accepted, instrument_btc
    ):
        payload = TradeCreate(
            order_id=order_accepted.id,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("0.5"),
            price=Decimal("68000"),
            currency="EUR",
            executed_at=datetime.now(timezone.utc),
        )
        trade = trade_service.record_trade(db, payload)
        assert trade.id is not None
        assert trade.execution_instruction_id is None
        assert trade.order_id == order_accepted.id


# ---------------------------------------------------------------------------
# Parent execution retry chain
# ---------------------------------------------------------------------------

class TestParentExecutionChain:

    def test_retry_with_terminal_parent(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        parent = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))
        service.mark_sent(db, parent.id)
        service.reject(db, parent.id, "rejected by venue")

        retry_payload = ExecutionCreate(
            order_id=order_accepted.id,
            parent_execution_id=parent.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1.0"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        retry = service.create_execution(db, retry_payload)
        assert retry.parent_execution_id == parent.id

    def test_retry_with_non_terminal_parent_rejected(
        self, db: Session, service: ExecutionService, order_accepted, instrument_btc
    ):
        parent = service.create_execution(db, _make_market_create(order_accepted, instrument_btc))

        retry_payload = ExecutionCreate(
            order_id=order_accepted.id,
            parent_execution_id=parent.id,
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1.0"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ParentExecutionNotTerminalError):
            service.create_execution(db, retry_payload)

    def test_retry_parent_not_found(self, db: Session, service: ExecutionService, order_accepted, instrument_btc):
        payload = ExecutionCreate(
            order_id=order_accepted.id,
            parent_execution_id=uuid.uuid4(),
            venue=ExecutionVenue.BINANCE,
            execution_type=ExecutionType.MARKET,
            instrument_id=instrument_btc.id,
            side="buy",
            quantity=Decimal("1.0"),
            currency="EUR",
            requested_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ParentExecutionReferenceError):
            service.create_execution(db, payload)
