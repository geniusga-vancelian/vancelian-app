"""Performance & Benchmark Engine (Phase 9).

Purely analytical, read-only layer. Never modifies:
- orders, executions, trades, settlements, ledger, positions,
  valuations, drift, strategy engine, orchestrator.

Important: The TWR implementation in v1 is snapshot-based and does not
isolate external cash flows. Future versions may introduce true
time-weighted return calculations using cash flow adjustments.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import sqrt
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import MarketDataBar1d
from ..instruments.models import Instrument
from ..portfolios.models import Portfolio
from ..valuations.models import PortfolioValuation
from .schemas import (
    BenchmarkComparison,
    PerformanceSeriesResponse,
    PerformanceSummary,
    ReturnSeriesPoint,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class PortfolioNotFoundForPerformanceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class PerformanceService:

    # ------------------------------------------------------------------
    # compute_portfolio_performance — summary metrics
    # ------------------------------------------------------------------

    def compute_portfolio_performance(
        self, db: Session, portfolio_id: UUID
    ) -> PerformanceSummary:
        self._validate_portfolio(db, portfolio_id)
        snapshots = self._load_snapshots(db, portfolio_id)
        warnings: list[str] = []

        if len(snapshots) < 2:
            warnings.append("Insufficient performance data: fewer than 2 valuation snapshots")
            return PerformanceSummary(
                portfolio_id=portfolio_id,
                data_points=len(snapshots),
                warnings=warnings,
            )

        series = self._build_series(snapshots, warnings)

        valid_returns = [
            r for r in (pt["period_return"] for pt in series)
            if r is not None
        ]

        total_return = series[-1]["cumulative_return"] if series else None
        max_dd = self._max_drawdown(series)
        vol = self._volatility(valid_returns)
        wr = self._winning_ratio(valid_returns)

        return PerformanceSummary(
            portfolio_id=portfolio_id,
            period_start=snapshots[0].valuation_timestamp,
            period_end=snapshots[-1].valuation_timestamp,
            total_return=self._fmt(total_return),
            max_drawdown=self._fmt(max_dd),
            volatility=self._fmt(vol),
            winning_days_ratio=self._fmt(wr),
            data_points=len(snapshots),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # compute_performance_series — full time series
    # ------------------------------------------------------------------

    def compute_performance_series(
        self, db: Session, portfolio_id: UUID
    ) -> PerformanceSeriesResponse:
        self._validate_portfolio(db, portfolio_id)
        snapshots = self._load_snapshots(db, portfolio_id)
        warnings: list[str] = []

        if len(snapshots) < 2:
            points = []
            if snapshots:
                nav = Decimal(str(snapshots[0].nav))
                points.append(ReturnSeriesPoint(
                    timestamp=snapshots[0].valuation_timestamp,
                    nav=str(nav),
                ))
            return PerformanceSeriesResponse(
                portfolio_id=portfolio_id,
                series=points,
                data_points=len(snapshots),
            )

        series = self._build_series(snapshots, warnings)

        points = [
            ReturnSeriesPoint(
                timestamp=pt["timestamp"],
                nav=str(pt["nav"]),
                period_return=self._fmt(pt["period_return"]),
                cumulative_return=self._fmt(pt["cumulative_return"]),
                drawdown=self._fmt(pt["drawdown"]),
            )
            for pt in series
        ]

        total_return = series[-1]["cumulative_return"] if series else None
        max_dd = self._max_drawdown(series)

        return PerformanceSeriesResponse(
            portfolio_id=portfolio_id,
            series=points,
            total_return=self._fmt(total_return),
            max_drawdown=self._fmt(max_dd),
            data_points=len(snapshots),
        )

    # ------------------------------------------------------------------
    # compare_to_benchmark
    # ------------------------------------------------------------------

    def compare_to_benchmark(
        self, db: Session, portfolio_id: UUID
    ) -> BenchmarkComparison:
        self._validate_portfolio(db, portfolio_id)
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        warnings: list[str] = []

        benchmark_cfg = (portfolio.metadata_ or {}).get("benchmark")
        if not benchmark_cfg or not benchmark_cfg.get("instrument_id"):
            warnings.append("No benchmark configured for this portfolio")
            return BenchmarkComparison(
                portfolio_id=portfolio_id,
                warnings=warnings,
            )

        benchmark_instrument_id = UUID(benchmark_cfg["instrument_id"])
        benchmark_label = benchmark_cfg.get("label")

        snapshots = self._load_snapshots(db, portfolio_id)
        if len(snapshots) < 2:
            warnings.append("Insufficient data for benchmark comparison")
            return BenchmarkComparison(
                portfolio_id=portfolio_id,
                benchmark_label=benchmark_label,
                benchmark_instrument_id=benchmark_instrument_id,
                warnings=warnings,
            )

        first_ts = snapshots[0].valuation_timestamp
        last_ts = snapshots[-1].valuation_timestamp

        benchmark_return = self._resolve_benchmark_return(
            db, benchmark_instrument_id, first_ts, last_ts, warnings,
        )

        portfolio_series = self._build_series(snapshots, [])
        portfolio_return = portfolio_series[-1]["cumulative_return"] if portfolio_series else None

        alpha = None
        if portfolio_return is not None and benchmark_return is not None:
            alpha = portfolio_return - benchmark_return

        return BenchmarkComparison(
            portfolio_id=portfolio_id,
            benchmark_label=benchmark_label,
            benchmark_instrument_id=benchmark_instrument_id,
            portfolio_return=self._fmt(portfolio_return),
            benchmark_return=self._fmt(benchmark_return),
            alpha=self._fmt(alpha),
            period_start=first_ts,
            period_end=last_ts,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal: build return series from snapshots
    # ------------------------------------------------------------------

    @staticmethod
    def _build_series(
        snapshots: list[PortfolioValuation],
        warnings: list[str],
    ) -> list[dict]:
        series: list[dict] = []
        cumulative = ONE
        peak = ZERO
        prev_nav: Optional[Decimal] = None

        for snap in snapshots:
            nav = Decimal(str(snap.nav))
            period_ret: Optional[Decimal] = None
            cum_ret: Optional[Decimal] = None

            if prev_nav is not None:
                if prev_nav <= ZERO:
                    period_ret = None
                    warnings.append(
                        f"Invalid NAV <= 0 at {snap.valuation_timestamp}; "
                        "period return set to None"
                    )
                else:
                    period_ret = (nav / prev_nav) - ONE
                    cumulative *= (ONE + period_ret)

            cum_ret = cumulative - ONE if prev_nav is not None else ZERO

            if nav > peak:
                peak = nav
            dd = ((nav - peak) / peak) if peak > ZERO else ZERO

            series.append({
                "timestamp": snap.valuation_timestamp,
                "nav": nav,
                "valuation_id": snap.id,
                "period_return": period_ret,
                "cumulative_return": cum_ret,
                "drawdown": dd,
            })

            prev_nav = nav

        return series

    # ------------------------------------------------------------------
    # Internal: benchmark resolution via historical 1d bars
    # ------------------------------------------------------------------

    def _resolve_benchmark_return(
        self,
        db: Session,
        pe_instrument_id: UUID,
        start_ts: datetime,
        end_ts: datetime,
        warnings: list[str],
    ) -> Optional[Decimal]:
        instrument = (
            db.query(Instrument)
            .filter(Instrument.id == pe_instrument_id)
            .first()
        )
        if instrument is None:
            warnings.append("Benchmark instrument not found")
            return None

        md_id = (instrument.metadata_ or {}).get("market_data_instrument_id")
        if md_id is None:
            warnings.append("Benchmark instrument has no market_data_instrument_id")
            return None

        md_id_int = int(md_id)

        start_bar = (
            db.query(MarketDataBar1d)
            .filter(
                MarketDataBar1d.instrument_id == md_id_int,
                MarketDataBar1d.open_time <= start_ts,
            )
            .order_by(MarketDataBar1d.open_time.desc())
            .first()
        )
        end_bar = (
            db.query(MarketDataBar1d)
            .filter(
                MarketDataBar1d.instrument_id == md_id_int,
                MarketDataBar1d.open_time <= end_ts,
            )
            .order_by(MarketDataBar1d.open_time.desc())
            .first()
        )

        if start_bar is None or end_bar is None:
            warnings.append("Benchmark historical price data unavailable")
            return None

        price_start = Decimal(str(start_bar.close))
        price_end = Decimal(str(end_bar.close))

        if price_start <= ZERO:
            warnings.append("Benchmark start price is zero or negative")
            return None

        return (price_end / price_start) - ONE

    # ------------------------------------------------------------------
    # Internal: statistical helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _max_drawdown(series: list[dict]) -> Optional[Decimal]:
        if not series:
            return None
        min_dd = min(
            (pt["drawdown"] for pt in series if pt["drawdown"] is not None),
            default=None,
        )
        return min_dd

    @staticmethod
    def _volatility(returns: list[Decimal]) -> Optional[Decimal]:
        """Per-period volatility (not annualized)."""
        if len(returns) < 2:
            return None
        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
        try:
            vol = Decimal(str(sqrt(float(variance))))
        except (ValueError, InvalidOperation):
            return None
        return vol.quantize(Decimal("0.0000000001"))

    @staticmethod
    def _winning_ratio(returns: list[Decimal]) -> Optional[Decimal]:
        if not returns:
            return None
        winners = sum(1 for r in returns if r > ZERO)
        ratio = Decimal(winners) / Decimal(len(returns))
        return ratio.quantize(Decimal("0.0001"))

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_portfolio(db: Session, portfolio_id: UUID) -> None:
        exists = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if exists is None:
            raise PortfolioNotFoundForPerformanceError(portfolio_id)

    @staticmethod
    def _load_snapshots(
        db: Session, portfolio_id: UUID
    ) -> list[PortfolioValuation]:
        return (
            db.query(PortfolioValuation)
            .filter(PortfolioValuation.portfolio_id == portfolio_id)
            .order_by(PortfolioValuation.valuation_timestamp.asc())
            .all()
        )

    @staticmethod
    def _fmt(val: Optional[Decimal]) -> Optional[str]:
        if val is None:
            return None
        return str(val.quantize(Decimal("0.0000000001")))
