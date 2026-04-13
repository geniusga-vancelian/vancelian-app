"""Tests for Portfolio Engine — Valuation & Performance Engine (Phase 5)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.instruments.price_bridge import (
    MarketDataLinkMissingError,
    QuoteNotAvailableError,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.valuations.models import (
    PortfolioValuation,
    PositionValuation,
)
from services.portfolio_engine.valuations.service import (
    PortfolioNotFoundForValuationError,
    PositionNotFoundForValuationError,
    ValuationService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> ValuationService:
    return ValuationService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Valuation Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol=f"VAL_BTC_{uuid.uuid4().hex[:4]}",
        name="Bitcoin",
        asset_type="crypto",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_eth(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol=f"VAL_ETH_{uuid.uuid4().hex[:4]}",
        name="Ethereum",
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
        code=f"VAL_BTC-SPOT-{uuid.uuid4().hex[:4]}",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 9901},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_eth: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_eth.id,
        code=f"VAL_ETH-SPOT-{uuid.uuid4().hex[:4]}",
        name="ETH Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 9902},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_vault(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code=f"VAL_VAULT-{uuid.uuid4().hex[:4]}",
        name="Vault Token",
        instrument_type="vault_units",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def position_btc(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="open",
        quantity=Decimal("0.5"),
        available_quantity=Decimal("0.5"),
        average_entry_price=Decimal("68000"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_eth(db: Session, portfolio: Portfolio, instrument_eth: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_eth.id,
        position_type="spot",
        status="open",
        quantity=Decimal("10"),
        available_quantity=Decimal("10"),
        average_entry_price=Decimal("3500"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_vault(db: Session, portfolio: Portfolio, instrument_vault: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_vault.id,
        position_type="vault_units",
        status="open",
        quantity=Decimal("1000"),
        available_quantity=Decimal("1000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_no_avg(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    """Position with no average_entry_price (legacy/anomaly)."""
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="open",
        quantity=Decimal("1"),
        available_quantity=Decimal("1"),
        average_entry_price=None,
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def closed_position_with_pnl(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="closed",
        quantity=Decimal("0"),
        available_quantity=Decimal("0"),
        average_entry_price=Decimal("50000"),
        realized_pnl=Decimal("5000"),
        closed_at=datetime.now(timezone.utc),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


PRICE_BRIDGE_PATH = "services.portfolio_engine.valuations.service.get_instrument_price"


# ---------------------------------------------------------------------------
# 1. Single priced position valuation
# ---------------------------------------------------------------------------

class TestSinglePositionValuation:

    @patch(PRICE_BRIDGE_PATH)
    def test_priced_position(
        self, mock_price, db: Session, svc: ValuationService,
        position_btc: PositionAtom, instrument_btc: Instrument,
    ):
        mock_price.return_value = {"price": "70000.00"}

        result = svc.value_position(db, position_btc.id)

        assert result.pricing_status == "priced"
        assert result.price == "70000.00"
        assert result.market_value == "35000.00"
        assert result.quantity == "0.5000000000"
        assert result.position_type == "spot"


# ---------------------------------------------------------------------------
# 2. Unrealized PnL calculation
# ---------------------------------------------------------------------------

class TestUnrealizedPnl:

    @patch(PRICE_BRIDGE_PATH)
    def test_unrealized_pnl_positive(
        self, mock_price, db: Session, svc: ValuationService,
        position_btc: PositionAtom,
    ):
        mock_price.return_value = {"price": "70000.00"}
        result = svc.value_position(db, position_btc.id)

        expected = Decimal("0.5") * (Decimal("70000") - Decimal("68000"))
        assert Decimal(result.unrealized_pnl) == expected.quantize(Decimal("0.01"))

    @patch(PRICE_BRIDGE_PATH)
    def test_unrealized_pnl_negative(
        self, mock_price, db: Session, svc: ValuationService,
        position_btc: PositionAtom,
    ):
        mock_price.return_value = {"price": "66000.00"}
        result = svc.value_position(db, position_btc.id)

        expected = Decimal("0.5") * (Decimal("66000") - Decimal("68000"))
        assert Decimal(result.unrealized_pnl) == expected.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# 3. Portfolio NAV aggregation
# ---------------------------------------------------------------------------

class TestPortfolioNAV:

    @patch(PRICE_BRIDGE_PATH)
    def test_nav_multiple_positions(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom, position_eth: PositionAtom,
        instrument_btc: Instrument, instrument_eth: Instrument,
    ):
        def price_side_effect(session, instr_id):
            if instr_id == instrument_btc.id:
                return {"price": "70000.00"}
            if instr_id == instrument_eth.id:
                return {"price": "4000.00"}
            raise MarketDataLinkMissingError(instr_id)

        mock_price.side_effect = price_side_effect

        result = svc.value_portfolio(db, portfolio.id)

        btc_mv = Decimal("0.5") * Decimal("70000")
        eth_mv = Decimal("10") * Decimal("4000")
        expected_nav = (btc_mv + eth_mv).quantize(Decimal("0.01"))

        assert Decimal(result.nav) == expected_nav
        assert result.priced_positions_count == 2


# ---------------------------------------------------------------------------
# 4. Allocation weight calculation
# ---------------------------------------------------------------------------

class TestAllocationWeights:

    @patch(PRICE_BRIDGE_PATH)
    def test_allocation_weights_sum_to_one(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom, position_eth: PositionAtom,
        instrument_btc: Instrument, instrument_eth: Instrument,
    ):
        def price_side_effect(session, instr_id):
            if instr_id == instrument_btc.id:
                return {"price": "60000.00"}
            if instr_id == instrument_eth.id:
                return {"price": "4000.00"}
            raise MarketDataLinkMissingError(instr_id)

        mock_price.side_effect = price_side_effect

        result = svc.value_portfolio(db, portfolio.id)

        weights = [Decimal(p.allocation_weight) for p in result.positions if p.allocation_weight]
        assert sum(weights) == Decimal("1.000000")


# ---------------------------------------------------------------------------
# 5. Missing price handling
# ---------------------------------------------------------------------------

class TestMissingPrice:

    @patch(PRICE_BRIDGE_PATH)
    def test_missing_price_does_not_break_valuation(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom,
    ):
        mock_price.side_effect = MarketDataLinkMissingError(uuid.uuid4())

        result = svc.value_portfolio(db, portfolio.id)

        assert result.priced_positions_count == 0
        assert result.unpriced_positions_count == 1
        assert Decimal(result.nav) == Decimal("0")
        assert len(result.warnings) >= 1

    @patch(PRICE_BRIDGE_PATH)
    def test_quote_not_available(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom,
    ):
        mock_price.side_effect = QuoteNotAvailableError(1)

        result = svc.value_portfolio(db, portfolio.id)

        assert result.unpriced_positions_count == 1
        assert result.positions[0].pricing_status == "unpriced"
        assert result.positions[0].price is None


# ---------------------------------------------------------------------------
# 6. Unsupported position_type handling
# ---------------------------------------------------------------------------

class TestUnsupportedPositionType:

    @patch(PRICE_BRIDGE_PATH)
    def test_vault_position_unpriced(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_vault: PositionAtom,
    ):
        result = svc.value_portfolio(db, portfolio.id)

        assert result.unpriced_positions_count == 1
        assert result.positions[0].pricing_status == "unpriced"
        assert result.positions[0].position_type == "vault_units"
        mock_price.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Missing average_entry_price -> unrealized = 0 + warning
# ---------------------------------------------------------------------------

class TestMissingAverageEntryPrice:

    @patch(PRICE_BRIDGE_PATH)
    def test_no_avg_price_unrealized_zero_with_warning(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_no_avg: PositionAtom,
    ):
        mock_price.return_value = {"price": "70000.00"}

        result = svc.value_portfolio(db, portfolio.id)

        assert result.priced_positions_count == 1
        pos = result.positions[0]
        assert pos.unrealized_pnl == "0"
        assert pos.average_entry_price is None

        avg_warnings = [w for w in result.warnings if "average entry price" in w]
        assert len(avg_warnings) == 1


# ---------------------------------------------------------------------------
# 8. Realized + unrealized aggregation
# ---------------------------------------------------------------------------

class TestPnlAggregation:

    @patch(PRICE_BRIDGE_PATH)
    def test_total_pnl_equals_realized_plus_unrealized(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom,
    ):
        mock_price.return_value = {"price": "70000.00"}

        result = svc.value_portfolio(db, portfolio.id)

        total_realized = Decimal(result.total_realized_pnl)
        total_unrealized = Decimal(result.total_unrealized_pnl)
        total_pnl = Decimal(result.total_pnl)
        assert total_pnl == total_realized + total_unrealized


# ---------------------------------------------------------------------------
# 9. Closed positions excluded from live list but included in total_realized
# ---------------------------------------------------------------------------

class TestClosedPositionRealized:

    @patch(PRICE_BRIDGE_PATH)
    def test_closed_position_realized_pnl_included(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio,
        position_btc: PositionAtom,
        closed_position_with_pnl: PositionAtom,
        instrument_btc: Instrument,
    ):
        mock_price.return_value = {"price": "70000.00"}

        result = svc.value_portfolio(db, portfolio.id)

        open_ids = [p.position_id for p in result.positions]
        assert position_btc.id in open_ids
        assert closed_position_with_pnl.id not in open_ids

        assert Decimal(result.total_realized_pnl) == Decimal("5000")

    @patch(PRICE_BRIDGE_PATH)
    def test_closed_position_only_contributes_realized(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio,
        closed_position_with_pnl: PositionAtom,
    ):
        result = svc.value_portfolio(db, portfolio.id)

        assert len(result.positions) == 0
        assert Decimal(result.nav) == Decimal("0")
        assert Decimal(result.total_realized_pnl) == Decimal("5000")
        assert Decimal(result.total_unrealized_pnl) == Decimal("0")
        assert Decimal(result.total_pnl) == Decimal("5000")


# ---------------------------------------------------------------------------
# 10. Snapshot creation
# ---------------------------------------------------------------------------

class TestSnapshotCreation:

    @patch(PRICE_BRIDGE_PATH)
    def test_create_snapshot_persists(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom, instrument_btc: Instrument,
    ):
        mock_price.return_value = {"price": "70000.00"}

        snapshot = svc.create_snapshot(db, portfolio.id)

        assert snapshot.portfolio_id == portfolio.id
        assert Decimal(snapshot.nav) == Decimal("35000.00")
        assert snapshot.valuation_source == "on_demand_snapshot"

        pv_count = db.query(PortfolioValuation).filter(
            PortfolioValuation.portfolio_id == portfolio.id
        ).count()
        assert pv_count == 1

        pos_val_count = db.query(PositionValuation).filter(
            PositionValuation.portfolio_id == portfolio.id
        ).count()
        assert pos_val_count == 1


# ---------------------------------------------------------------------------
# 11. Snapshot history listing
# ---------------------------------------------------------------------------

class TestSnapshotHistory:

    @patch(PRICE_BRIDGE_PATH)
    def test_list_snapshots(
        self, mock_price, db: Session, svc: ValuationService,
        portfolio: Portfolio, position_btc: PositionAtom, instrument_btc: Instrument,
    ):
        mock_price.return_value = {"price": "70000.00"}

        svc.create_snapshot(db, portfolio.id)
        svc.create_snapshot(db, portfolio.id)

        items, total = svc.list_snapshots(db, portfolio.id)
        assert total == 2
        assert len(items) == 2

    def test_list_snapshots_empty(
        self, db: Session, svc: ValuationService, portfolio: Portfolio,
    ):
        items, total = svc.list_snapshots(db, portfolio.id)
        assert total == 0
        assert items == []


# ---------------------------------------------------------------------------
# 12. Portfolio not found -> error
# ---------------------------------------------------------------------------

class TestPortfolioNotFound:

    def test_value_portfolio_not_found(self, db: Session, svc: ValuationService):
        with pytest.raises(PortfolioNotFoundForValuationError):
            svc.value_portfolio(db, uuid.uuid4())

    def test_list_snapshots_not_found(self, db: Session, svc: ValuationService):
        with pytest.raises(PortfolioNotFoundForValuationError):
            svc.list_snapshots(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# 13. Position not found -> error
# ---------------------------------------------------------------------------

class TestPositionNotFound:

    def test_value_position_not_found(self, db: Session, svc: ValuationService):
        with pytest.raises(PositionNotFoundForValuationError):
            svc.value_position(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# Empty portfolio
# ---------------------------------------------------------------------------

class TestEmptyPortfolio:

    def test_empty_portfolio_valuation(
        self, db: Session, svc: ValuationService, portfolio: Portfolio,
    ):
        result = svc.value_portfolio(db, portfolio.id)

        assert Decimal(result.nav) == Decimal("0")
        assert Decimal(result.total_realized_pnl) == Decimal("0")
        assert Decimal(result.total_unrealized_pnl) == Decimal("0")
        assert Decimal(result.total_pnl) == Decimal("0")
        assert result.priced_positions_count == 0
        assert result.unpriced_positions_count == 0
        assert result.positions == []
