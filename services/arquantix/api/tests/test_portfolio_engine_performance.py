"""Tests for Portfolio Engine — Performance & Benchmark Engine (Phase 9)."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.performance.service import (
    PerformanceService,
    PortfolioNotFoundForPerformanceError,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.valuations.models import PortfolioValuation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> PerformanceService:
    return PerformanceService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Performance Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


def _snap(db, portfolio, nav, days_ago=0, source="on_demand_snapshot"):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    s = PortfolioValuation(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        nav=Decimal(str(nav)),
        total_realized_pnl=Decimal("0"),
        total_unrealized_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        priced_positions_count=1,
        unpriced_positions_count=0,
        valuation_source=source,
        valuation_timestamp=ts,
    )
    db.add(s)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# 1. Time series generated from snapshots
# ---------------------------------------------------------------------------

class TestTimeSeries:

    def test_series_from_snapshots(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=3)
        _snap(db, portfolio, "10500", days_ago=2)
        _snap(db, portfolio, "11000", days_ago=1)

        result = svc.compute_performance_series(db, portfolio.id)

        assert result.data_points == 3
        assert len(result.series) == 3
        assert result.series[0].period_return is None or result.series[0].period_return == "0E-10"


# ---------------------------------------------------------------------------
# 2. Period return calculation
# ---------------------------------------------------------------------------

class TestPeriodReturn:

    def test_period_return_correct(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=2)
        _snap(db, portfolio, "11000", days_ago=1)

        result = svc.compute_performance_series(db, portfolio.id)
        ret = Decimal(result.series[1].period_return)
        assert ret == Decimal("0.1").quantize(Decimal("0.0000000001"))


# ---------------------------------------------------------------------------
# 3. Cumulative return calculation
# ---------------------------------------------------------------------------

class TestCumulativeReturn:

    def test_cumulative_return(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=3)
        _snap(db, portfolio, "11000", days_ago=2)
        _snap(db, portfolio, "12100", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)

        total = Decimal(result.total_return)
        expected = Decimal("0.21").quantize(Decimal("0.0000000001"))
        assert total == expected


# ---------------------------------------------------------------------------
# 4. Max drawdown detection
# ---------------------------------------------------------------------------

class TestMaxDrawdown:

    def test_drawdown_detected(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=4)
        _snap(db, portfolio, "12000", days_ago=3)
        _snap(db, portfolio, "9000", days_ago=2)
        _snap(db, portfolio, "11000", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)

        dd = Decimal(result.max_drawdown)
        expected = (Decimal("9000") - Decimal("12000")) / Decimal("12000")
        assert dd == expected.quantize(Decimal("0.0000000001"))


# ---------------------------------------------------------------------------
# 5. Volatility calculation
# ---------------------------------------------------------------------------

class TestVolatility:

    def test_volatility_computed(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=4)
        _snap(db, portfolio, "10500", days_ago=3)
        _snap(db, portfolio, "10200", days_ago=2)
        _snap(db, portfolio, "10800", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)
        assert result.volatility is not None
        vol = Decimal(result.volatility)
        assert vol > ZERO


# ---------------------------------------------------------------------------
# 6. Winning days ratio
# ---------------------------------------------------------------------------

class TestWinningRatio:

    def test_winning_ratio(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=4)
        _snap(db, portfolio, "11000", days_ago=3)
        _snap(db, portfolio, "10500", days_ago=2)
        _snap(db, portfolio, "11500", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)
        ratio = Decimal(result.winning_days_ratio)
        assert ratio == Decimal("0.6667").quantize(Decimal("0.0001"))


# ---------------------------------------------------------------------------
# 7. Fewer than 2 snapshots → warning
# ---------------------------------------------------------------------------

class TestInsufficientData:

    def test_single_snapshot_warning(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)
        assert result.data_points == 1
        assert result.total_return is None
        assert any("Insufficient" in w for w in result.warnings)

    def test_zero_snapshots_warning(self, db, svc, portfolio):
        result = svc.compute_portfolio_performance(db, portfolio.id)
        assert result.data_points == 0
        assert result.total_return is None


# ---------------------------------------------------------------------------
# 8. NAV <= 0 → invalid return
# ---------------------------------------------------------------------------

class TestInvalidNav:

    def test_nav_zero_period_return_none(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=3)
        _snap(db, portfolio, "0", days_ago=2)
        _snap(db, portfolio, "5000", days_ago=1)

        result = svc.compute_performance_series(db, portfolio.id)

        assert result.series[2].period_return is None
        summary = svc.compute_portfolio_performance(db, portfolio.id)
        assert any("Invalid NAV" in w or "invalid nav" in w.lower() for w in summary.warnings)


# ---------------------------------------------------------------------------
# 9. Benchmark comparison
# ---------------------------------------------------------------------------

class TestBenchmark:

    def test_benchmark_with_historical_data(self, db, svc, portfolio):
        from database import MarketDataBar1d, MarketDataInstrument

        md_instrument = MarketDataInstrument(
            symbol=f"PERFBTC{uuid.uuid4().hex[:4]}",
            name="Bitcoin",
            asset_class="crypto",
            provider="test",
        )
        db.add(md_instrument)
        db.flush()

        asset = Asset(
            id=uuid.uuid4(),
            symbol=f"PERF_BTC_{uuid.uuid4().hex[:4]}",
            name="Bitcoin",
            asset_type="crypto",
            metadata_={},
        )
        db.add(asset)
        db.flush()

        instrument = Instrument(
            id=uuid.uuid4(),
            asset_id=asset.id,
            code=f"PERF_BTC-SPOT-{uuid.uuid4().hex[:4]}",
            name="BTC Spot",
            instrument_type="spot",
            metadata_={"market_data_instrument_id": md_instrument.id},
        )
        db.add(instrument)
        db.flush()

        portfolio.metadata_ = {
            "benchmark": {
                "instrument_id": str(instrument.id),
                "label": "BTC",
            }
        }
        db.flush()

        now = datetime.now(timezone.utc)
        bar_start = MarketDataBar1d(
            instrument_id=md_instrument.id,
            open_time=now - timedelta(days=4),
            open=Decimal("60000"),
            high=Decimal("61000"),
            low=Decimal("59000"),
            close=Decimal("60000"),
            volume=Decimal("100"),
            source="test",
        )
        bar_end = MarketDataBar1d(
            instrument_id=md_instrument.id,
            open_time=now - timedelta(days=1),
            open=Decimal("65000"),
            high=Decimal("66000"),
            low=Decimal("64000"),
            close=Decimal("66000"),
            volume=Decimal("120"),
            source="test",
        )
        db.add_all([bar_start, bar_end])
        db.flush()

        _snap(db, portfolio, "10000", days_ago=3)
        _snap(db, portfolio, "11000", days_ago=0)

        result = svc.compare_to_benchmark(db, portfolio.id)

        assert result.benchmark_label == "BTC"
        assert result.benchmark_return is not None
        assert result.portfolio_return is not None
        assert result.alpha is not None

        bench_ret = Decimal(result.benchmark_return)
        expected_bench = (Decimal("66000") / Decimal("60000")) - 1
        assert bench_ret == expected_bench.quantize(Decimal("0.0000000001"))


# ---------------------------------------------------------------------------
# 10. No benchmark configured → warning
# ---------------------------------------------------------------------------

class TestNoBenchmark:

    def test_no_benchmark_warning(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=2)
        _snap(db, portfolio, "11000", days_ago=1)

        result = svc.compare_to_benchmark(db, portfolio.id)
        assert any("No benchmark" in w for w in result.warnings)
        assert result.benchmark_return is None
        assert result.alpha is None


# ---------------------------------------------------------------------------
# 11. Portfolio not found → 404
# ---------------------------------------------------------------------------

class TestPortfolioNotFound:

    def test_performance_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForPerformanceError):
            svc.compute_portfolio_performance(db, uuid.uuid4())

    def test_series_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForPerformanceError):
            svc.compute_performance_series(db, uuid.uuid4())

    def test_benchmark_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForPerformanceError):
            svc.compare_to_benchmark(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# 12. Constant NAV → returns = 0
# ---------------------------------------------------------------------------

class TestConstantNav:

    def test_constant_nav_zero_return(self, db, svc, portfolio):
        _snap(db, portfolio, "10000", days_ago=3)
        _snap(db, portfolio, "10000", days_ago=2)
        _snap(db, portfolio, "10000", days_ago=1)

        result = svc.compute_portfolio_performance(db, portfolio.id)

        assert Decimal(result.total_return) == Decimal("0").quantize(Decimal("0.0000000001"))
        assert Decimal(result.max_drawdown) == Decimal("0").quantize(Decimal("0.0000000001"))
        assert Decimal(result.volatility) == Decimal("0").quantize(Decimal("0.0000000001"))
        assert Decimal(result.winning_days_ratio) == Decimal("0").quantize(Decimal("0.0001"))


ZERO = Decimal("0")
