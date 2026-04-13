"""Rebuild / Replay service (Hardening Subphase 2).

Deterministic rebuild of derived portfolio state from source-of-truth layers.

Source-of-truth hierarchy:
    trades → positions → valuations → performance

Rules:
- Never rebuild from already-derived aggregates when a more primary source exists
- Every rebuild creates a pe_job_runs row
- Every rebuild logs audit events
- Scoped to one portfolio at a time
"""
import logging
import traceback
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..audit_service import AuditService
from .models import JobRun
from .repository import JobRunRepository
from .schemas import RebuildResult

logger = logging.getLogger(__name__)

_job_repo = JobRunRepository()
_audit = AuditService()


class PortfolioNotFoundForRebuildError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class RebuildService:

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_rebuild_job(
        self, db: Session, *, job_type: str, portfolio_id: UUID,
    ) -> RebuildResult:
        self._validate_portfolio(db, portfolio_id)

        job_run = _job_repo.create(db, data={
            "job_type": job_type,
            "scope_type": "portfolio",
            "scope_id": str(portfolio_id),
            "status": "started",
            "started_at": datetime.now(timezone.utc),
        })
        db.flush()

        try:
            if job_type == "rebuild_positions":
                result = self._rebuild_positions(db, portfolio_id, job_run)
            elif job_type == "rebuild_valuations":
                result = self._rebuild_valuations(db, portfolio_id, job_run)
            elif job_type == "rebuild_performance":
                result = self._rebuild_performance(db, portfolio_id, job_run)
            else:
                raise ValueError(f"Unknown job_type: {job_type}")

            _job_repo.mark_completed(db, job_run, metadata={
                "records_processed": result.records_processed,
            })
            _audit.log_success(
                db,
                entity_type="portfolio",
                entity_id=str(portfolio_id),
                action=f"{job_type.replace('rebuild_', '')}_rebuilt",
                metadata={"job_run_id": str(job_run.id)},
            )
            return result

        except PortfolioNotFoundForRebuildError:
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            _job_repo.mark_failed(db, job_run, error_message=error_msg)
            _audit.log_failure(
                db,
                entity_type="portfolio",
                entity_id=str(portfolio_id),
                action=f"{job_type.replace('rebuild_', '')}_rebuilt",
                error=error_msg,
                metadata={"job_run_id": str(job_run.id)},
            )
            logger.exception("Rebuild job %s failed for portfolio %s", job_type, portfolio_id)
            return RebuildResult(
                job_run_id=job_run.id,
                portfolio_id=portfolio_id,
                job_type=job_type,
                status="failed",
                error_message=error_msg,
            )

    # ------------------------------------------------------------------
    # rebuild_positions: delete + replay from trades
    # ------------------------------------------------------------------

    def _rebuild_positions(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> RebuildResult:
        from ...orders.models import Order
        from ...positions.models import PositionAtom
        from ...positions.service import PositionAtomService
        from ...trades.models import Trade

        trades = (
            db.query(Trade)
            .join(Order, Trade.order_id == Order.id)
            .filter(Order.portfolio_id == portfolio_id)
            .order_by(Trade.executed_at.asc())
            .all()
        )

        deleted = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio_id)
            .delete(synchronize_session="fetch")
        )
        db.flush()

        warnings: list[str] = []
        position_svc = PositionAtomService()

        for trade in trades:
            try:
                position_svc.apply_trade(db, trade)
            except Exception as exc:
                warnings.append(f"Trade {trade.id}: {type(exc).__name__}: {exc}")

        return RebuildResult(
            job_run_id=job_run.id,
            portfolio_id=portfolio_id,
            job_type="rebuild_positions",
            status="completed",
            records_processed=len(trades),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # rebuild_valuations: create fresh snapshot from current positions
    # ------------------------------------------------------------------

    def _rebuild_valuations(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> RebuildResult:
        from ...valuations.service import ValuationService
        from ...valuations.enums import ValuationSource

        valuation_svc = ValuationService()
        valuation = valuation_svc.value_portfolio(db, portfolio_id)

        from ...valuations.repository import ValuationRepository
        from decimal import Decimal
        repo = ValuationRepository()

        ts = valuation.valuation_timestamp
        for pos_val in valuation.positions:
            repo.create_position_valuation(db, data={
                "position_id": pos_val.position_id,
                "portfolio_id": portfolio_id,
                "instrument_id": pos_val.instrument_id,
                "quantity": Decimal(pos_val.quantity),
                "price": Decimal(pos_val.price) if pos_val.price else None,
                "market_value": Decimal(pos_val.market_value) if pos_val.market_value else None,
                "average_entry_price": Decimal(pos_val.average_entry_price) if pos_val.average_entry_price else None,
                "unrealized_pnl": Decimal(pos_val.unrealized_pnl) if pos_val.unrealized_pnl else None,
                "realized_pnl": Decimal(pos_val.realized_pnl),
                "pricing_status": pos_val.pricing_status,
                "valuation_timestamp": ts,
            })

        repo.create_portfolio_valuation(db, data={
            "portfolio_id": portfolio_id,
            "nav": Decimal(valuation.nav),
            "total_realized_pnl": Decimal(valuation.total_realized_pnl),
            "total_unrealized_pnl": Decimal(valuation.total_unrealized_pnl),
            "total_pnl": Decimal(valuation.total_pnl),
            "priced_positions_count": valuation.priced_positions_count,
            "unpriced_positions_count": valuation.unpriced_positions_count,
            "valuation_source": ValuationSource.MANUAL_REBUILD,
            "valuation_timestamp": ts,
            "metadata_": {},
        })

        return RebuildResult(
            job_run_id=job_run.id,
            portfolio_id=portfolio_id,
            job_type="rebuild_valuations",
            status="completed",
            records_processed=1,
        )

    # ------------------------------------------------------------------
    # rebuild_performance: clear + recompute from valuation snapshots
    # ------------------------------------------------------------------

    def _rebuild_performance(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> RebuildResult:
        from ...performance.models import PortfolioReturnSeries
        from ...performance.repository import PerformanceRepository
        from ...performance.service import PerformanceService
        from ...valuations.models import PortfolioValuation

        deleted = (
            db.query(PortfolioReturnSeries)
            .filter(PortfolioReturnSeries.portfolio_id == portfolio_id)
            .delete(synchronize_session="fetch")
        )
        db.flush()

        perf_svc = PerformanceService()
        snapshots = perf_svc._load_snapshots(db, portfolio_id)
        warnings: list[str] = []

        if len(snapshots) < 2:
            warnings.append("Fewer than 2 valuation snapshots; no return series generated")
            return RebuildResult(
                job_run_id=job_run.id,
                portfolio_id=portfolio_id,
                job_type="rebuild_performance",
                status="completed",
                records_processed=0,
                warnings=warnings,
            )

        series = perf_svc._build_series(snapshots, warnings)

        rows = [
            {
                "portfolio_id": portfolio_id,
                "valuation_id": pt["valuation_id"],
                "timestamp": pt["timestamp"],
                "nav": pt["nav"],
                "period_return": pt["period_return"],
                "cumulative_return": pt["cumulative_return"],
                "drawdown": pt["drawdown"],
                "metadata_": {"source": "rebuild"},
            }
            for pt in series
        ]

        perf_repo = PerformanceRepository()
        perf_repo.create_series_batch(db, rows=rows)

        return RebuildResult(
            job_run_id=job_run.id,
            portfolio_id=portfolio_id,
            job_type="rebuild_performance",
            status="completed",
            records_processed=len(rows),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_portfolio(db: Session, portfolio_id: UUID) -> None:
        from ...portfolios.models import Portfolio
        exists = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if exists is None:
            raise PortfolioNotFoundForRebuildError(portfolio_id)
