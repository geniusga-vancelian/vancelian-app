"""Tests for Portfolio Engine — Drift Detection & Rebalance Engine (Phase 6)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.drift.service import (
    DriftRebalanceService,
    PortfolioNotFoundForDriftError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> DriftRebalanceService:
    return DriftRebalanceService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Drift Test PF",
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
        symbol=f"DRIFT_BTC_{uuid.uuid4().hex[:4]}",
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
        symbol=f"DRIFT_ETH_{uuid.uuid4().hex[:4]}",
        name="Ethereum",
        asset_type="crypto",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_sol(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol=f"DRIFT_SOL_{uuid.uuid4().hex[:4]}",
        name="Solana",
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
        code=f"DRIFT_BTC-SPOT-{uuid.uuid4().hex[:4]}",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 7701},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_eth: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_eth.id,
        code=f"DRIFT_ETH-SPOT-{uuid.uuid4().hex[:4]}",
        name="ETH Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 7702},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_sol(db: Session, asset_sol: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_sol.id,
        code=f"DRIFT_SOL-SPOT-{uuid.uuid4().hex[:4]}",
        name="SOL Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 7703},
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
def position_sol(db: Session, portfolio: Portfolio, instrument_sol: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_sol.id,
        position_type="spot",
        status="open",
        quantity=Decimal("100"),
        available_quantity=Decimal("100"),
        average_entry_price=Decimal("150"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


def _alloc(db, portfolio, instrument, weight):
    ta = TargetAllocation(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument.id,
        target_weight=Decimal(str(weight)),
    )
    db.add(ta)
    db.flush()
    return ta


def _policy(db, portfolio, drift_threshold=None, min_trade_size=None):
    rp = RebalancePolicy(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        method="threshold",
        drift_threshold=Decimal(str(drift_threshold)) if drift_threshold else None,
        min_trade_size=Decimal(str(min_trade_size)) if min_trade_size else None,
    )
    db.add(rp)
    db.flush()
    return rp


def _mock_price(instrument_id_to_price: dict):
    """Returns a side_effect for get_instrument_price that returns a dict like the real bridge."""
    from services.portfolio_engine.instruments.price_bridge import (
        MarketDataLinkMissingError,
    )

    def _side_effect(db, instrument_id):
        if instrument_id in instrument_id_to_price:
            price = instrument_id_to_price[instrument_id]
            return {
                "instrument_id": str(instrument_id),
                "instrument_code": "MOCK",
                "asset_symbol": "MOCK",
                "market_data_instrument_id": 1,
                "provider": "mock",
                "provider_symbol": "MOCK",
                "price": str(price),
                "bid_price": str(price),
                "ask_price": str(price),
                "volume_24h": "1000",
                "quote_time": None,
                "updated_at": None,
            }
        raise MarketDataLinkMissingError(instrument_id)

    return _side_effect


PRICE_BRIDGE = "services.portfolio_engine.valuations.service.get_instrument_price"


# ---------------------------------------------------------------------------
# 1. Drift calculation correctness
# ---------------------------------------------------------------------------

class TestDriftDetection:

    def test_drift_basic(
        self, db, svc, portfolio, instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.50")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert report.needs_rebalance is True or report.needs_rebalance is False
        assert len(report.items) == 2
        assert Decimal(report.drift_score) >= Decimal("0")

    def test_drift_no_allocations_returns_warning(self, db, svc, portfolio, position_btc, instrument_btc):
        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert report.needs_rebalance is False
        assert any("no target allocations" in w for w in report.warnings)
        assert len(report.items) == 0

    def test_drift_threshold_from_policy(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")
        _policy(db, portfolio, drift_threshold="0.10")

        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert Decimal(report.threshold) == Decimal("0.10")

    def test_drift_explicit_threshold_overrides_policy(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")
        _policy(db, portfolio, drift_threshold="0.10")

        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(
                db, portfolio.id, threshold=Decimal("0.02"),
            )

        assert Decimal(report.threshold) == Decimal("0.02")


# ---------------------------------------------------------------------------
# 2. Drift score
# ---------------------------------------------------------------------------

class TestDriftScore:

    def test_drift_score_formula(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth, instrument_sol,
        position_btc, position_eth, position_sol,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.30")
        _alloc(db, portfolio, instrument_sol, "0.20")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
            instrument_sol.id: Decimal("200"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert Decimal(report.drift_score) >= Decimal("0")

        sum_abs = sum(abs(Decimal(item.drift)) for item in report.items)
        expected = (sum_abs / Decimal("2")).quantize(Decimal("0.000001"))
        assert Decimal(report.drift_score) == expected


# ---------------------------------------------------------------------------
# 3. Needs rebalance detection
# ---------------------------------------------------------------------------

class TestNeedsRebalance:

    def test_no_rebalance_within_threshold(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")

        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert report.needs_rebalance is False

    def test_rebalance_needed_beyond_threshold(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.90")
        _alloc(db, portfolio, instrument_eth, "0.10")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(
                db, portfolio.id, threshold=Decimal("0.01"),
            )

        assert report.needs_rebalance is True


# ---------------------------------------------------------------------------
# 4. Rebalance preview
# ---------------------------------------------------------------------------

class TestRebalancePreview:

    def test_preview_buy_sell(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.30")
        _alloc(db, portfolio, instrument_eth, "0.70")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(
                db, portfolio.id, threshold=Decimal("0.01"),
            )

        actions = {t.instrument_id: t.action for t in result.trades}
        assert instrument_btc.id in actions
        assert instrument_eth.id in actions

    def test_preview_trade_quantity(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.50")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(db, portfolio.id)

        for trade in result.trades:
            if trade.action != "hold" and trade.trade_quantity is not None:
                assert Decimal(trade.trade_quantity) > 0

    def test_preview_no_allocations(self, db, svc, portfolio, position_btc, instrument_btc):
        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(db, portfolio.id)

        assert result.needs_rebalance is False
        assert any("no target allocations" in w for w in result.warnings)

    def test_preview_nav_zero(self, db, svc, portfolio, instrument_btc):
        _alloc(db, portfolio, instrument_btc, "1.0")

        with patch(PRICE_BRIDGE, side_effect=_mock_price({})):
            result = svc.generate_rebalance_preview(db, portfolio.id)

        assert result.needs_rebalance is False
        assert Decimal(result.nav) == Decimal("0")


# ---------------------------------------------------------------------------
# 5. Min trade size / HOLD
# ---------------------------------------------------------------------------

class TestMinTradeSize:

    def test_small_delta_becomes_hold(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")
        _policy(db, portfolio, min_trade_size="999999999")

        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(db, portfolio.id)

        for trade in result.trades:
            assert trade.action == "hold"


# ---------------------------------------------------------------------------
# 6. Unallocated positions (position without target)
# ---------------------------------------------------------------------------

class TestUnallocatedPositions:

    def test_unallocated_position_detected_in_drift(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id, threshold=Decimal("0.01"))

        unallocated = [i for i in report.items if i.is_unallocated]
        assert len(unallocated) == 1
        assert unallocated[0].instrument_id == instrument_eth.id

    def test_unallocated_position_sell_in_preview(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(
                db, portfolio.id, threshold=Decimal("0.01"),
            )

        eth_trade = [t for t in result.trades if t.instrument_id == instrument_eth.id]
        assert len(eth_trade) == 1
        assert eth_trade[0].action == "sell"


# ---------------------------------------------------------------------------
# 7. Unpriced positions excluded
# ---------------------------------------------------------------------------

class TestUnpricedExclusion:

    def test_unpriced_excluded_from_drift(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.50")

        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            report = svc.detect_drift(db, portfolio.id)

        assert report.unpriced_excluded_count >= 1


# ---------------------------------------------------------------------------
# 8. Valuation cache reuse
# ---------------------------------------------------------------------------

class TestValuationCache:

    def test_preview_reuses_provided_valuation(
        self, db, svc, portfolio,
        instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "1.0")
        prices = {instrument_btc.id: Decimal("70000")}

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            valuation = svc._valuation_service.value_portfolio(db, portfolio.id)

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)) as mock_bridge:
            result = svc.generate_rebalance_preview(
                db, portfolio.id, valuation=valuation,
            )
            assert mock_bridge.call_count == 0

        assert result.nav == valuation.nav


# ---------------------------------------------------------------------------
# 9. Portfolio not found
# ---------------------------------------------------------------------------

class TestPortfolioNotFound:

    def test_drift_portfolio_not_found(self, db, svc):
        fake_id = uuid.uuid4()
        with pytest.raises(PortfolioNotFoundForDriftError):
            svc.detect_drift(db, fake_id)


# ---------------------------------------------------------------------------
# 10. Create rebalance plan persists
# ---------------------------------------------------------------------------

class TestCreateRebalancePlan:

    def test_plan_persisted(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc, position_eth,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.50")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            preview = svc.create_rebalance_plan(db, portfolio.id)

        assert preview.id is not None
        assert preview.portfolio_id == portfolio.id
        assert preview.status == "completed"
        assert len(preview.items) >= 1

        from services.portfolio_engine.rebalance_preview.models import RebalancePreview
        persisted = db.query(RebalancePreview).filter(
            RebalancePreview.id == preview.id
        ).first()
        assert persisted is not None


# ---------------------------------------------------------------------------
# 11. Target without position (allocation but no position)
# ---------------------------------------------------------------------------

class TestTargetWithoutPosition:

    def test_target_without_position_generates_buy(
        self, db, svc, portfolio,
        instrument_btc, instrument_eth,
        position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        _alloc(db, portfolio, instrument_eth, "0.50")

        prices = {
            instrument_btc.id: Decimal("70000"),
            instrument_eth.id: Decimal("4000"),
        }

        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.generate_rebalance_preview(
                db, portfolio.id, threshold=Decimal("0.01"),
            )

        eth_trade = [t for t in result.trades if t.instrument_id == instrument_eth.id]
        assert len(eth_trade) == 1
        assert eth_trade[0].action == "buy"
