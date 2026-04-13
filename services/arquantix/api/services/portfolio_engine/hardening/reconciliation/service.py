"""Reconciliation Engine (Hardening Subphase 3).

Read-only with respect to source-of-truth layers.
Only writes: reconciliation reports, job runs, audit events.

Sign convention for ledger: debit = +amount, credit = −amount.
expected_balance = Σ(debit amounts) − Σ(credit amounts)
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func as sqla_func
from sqlalchemy.orm import Session

from ..audit_service import AuditService
from ..jobs.models import JobRun
from ..jobs.repository import JobRunRepository
from .models import ReconciliationReport
from .repository import ReconciliationReportRepository
from .schemas import ReconciliationResult

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
_job_repo = JobRunRepository()
_report_repo = ReconciliationReportRepository()
_audit = AuditService()


class PortfolioNotFoundForReconciliationError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} not found")


class ReconciliationService:

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_reconciliation_job(
        self,
        db: Session,
        *,
        reconciliation_type: str,
        portfolio_id: Optional[UUID] = None,
    ) -> ReconciliationResult:
        scope_type = "portfolio" if portfolio_id else "global"
        scope_id = str(portfolio_id) if portfolio_id else None

        if portfolio_id:
            self._validate_portfolio(db, portfolio_id)

        job_run = _job_repo.create(db, data={
            "job_type": f"reconciliation_{reconciliation_type}",
            "scope_type": scope_type,
            "scope_id": scope_id,
            "status": "started",
            "started_at": datetime.now(timezone.utc),
        })
        db.flush()

        try:
            if reconciliation_type == "trades_vs_positions":
                result = self._reconcile_trades_vs_positions(db, portfolio_id, job_run)
            elif reconciliation_type == "positions_vs_valuations":
                result = self._reconcile_positions_vs_valuations(db, portfolio_id, job_run)
            elif reconciliation_type == "ledger_entries_vs_balances":
                result = self._reconcile_ledger_entries_vs_balances(db, job_run)
            elif reconciliation_type == "valuations_vs_performance":
                result = self._reconcile_valuations_vs_performance(db, portfolio_id, job_run)
            else:
                raise ValueError(f"Unknown reconciliation_type: {reconciliation_type}")

            _job_repo.mark_completed(db, job_run, metadata={
                "differences_found": result.differences_found,
            })

            audit_action = reconciliation_type.replace("_vs_", "_") + "_reconciled"
            _audit.log_success(
                db,
                entity_type=scope_type,
                entity_id=scope_id,
                action=audit_action,
                metadata={
                    "job_run_id": str(job_run.id),
                    "reconciliation_report_id": str(result.reconciliation_report_id),
                    "status": result.status,
                    "differences_found": result.differences_found,
                },
            )
            return result

        except PortfolioNotFoundForReconciliationError:
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            _job_repo.mark_failed(db, job_run, error_message=error_msg)
            audit_action = reconciliation_type.replace("_vs_", "_") + "_reconciled"
            _audit.log_failure(
                db,
                entity_type=scope_type,
                entity_id=scope_id,
                action=audit_action,
                error=error_msg,
                metadata={"job_run_id": str(job_run.id)},
            )
            logger.exception("Reconciliation %s failed", reconciliation_type)
            raise

    # ------------------------------------------------------------------
    # trades_vs_positions
    # ------------------------------------------------------------------

    def _reconcile_trades_vs_positions(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> ReconciliationResult:
        from ...orders.models import Order
        from ...positions.models import PositionAtom
        from ...trades.models import Trade

        trades = (
            db.query(Trade)
            .join(Order, Trade.order_id == Order.id)
            .filter(Order.portfolio_id == portfolio_id)
            .all()
        )

        expected: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for t in trades:
            iid = str(t.instrument_id)
            qty = Decimal(str(t.quantity))
            if t.side == "buy":
                expected[iid] += qty
            elif t.side == "sell":
                expected[iid] -= qty

        positions = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio_id)
            .all()
        )

        actual: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for p in positions:
            iid = str(p.instrument_id)
            actual[iid] += Decimal(str(p.quantity))

        all_instruments = set(expected.keys()) | set(actual.keys())
        mismatches = []
        for iid in sorted(all_instruments):
            exp = expected[iid]
            act = actual[iid]
            if exp != act:
                mismatches.append({
                    "instrument_id": iid,
                    "expected_quantity": str(exp),
                    "actual_quantity": str(act),
                    "difference": str(act - exp),
                })

        status = "matched" if not mismatches else "mismatched"
        meta = {
            "checked_instruments": len(all_instruments),
            "mismatches": mismatches,
        }

        report = _report_repo.create(db, data={
            "reconciliation_type": "trades_vs_positions",
            "scope_type": "portfolio",
            "scope_id": str(portfolio_id),
            "status": status,
            "differences_found": len(mismatches),
            "metadata_": meta,
        })

        return ReconciliationResult(
            job_run_id=job_run.id,
            reconciliation_report_id=report.id,
            reconciliation_type="trades_vs_positions",
            scope_type="portfolio",
            scope_id=str(portfolio_id),
            status=status,
            differences_found=len(mismatches),
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # positions_vs_valuations
    # ------------------------------------------------------------------

    def _reconcile_positions_vs_valuations(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> ReconciliationResult:
        from ...positions.models import PositionAtom
        from ...valuations.models import PortfolioValuation, PositionValuation

        open_positions = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        latest_pv = (
            db.query(PortfolioValuation)
            .filter(PortfolioValuation.portfolio_id == portfolio_id)
            .order_by(PortfolioValuation.valuation_timestamp.desc())
            .first()
        )

        warnings: list[str] = []
        if latest_pv is None:
            warnings.append("No valuation snapshot found for this portfolio")
            report = _report_repo.create(db, data={
                "reconciliation_type": "positions_vs_valuations",
                "scope_type": "portfolio",
                "scope_id": str(portfolio_id),
                "status": "matched" if not open_positions else "mismatched",
                "differences_found": len(open_positions),
                "metadata_": {
                    "valuation_timestamp": None,
                    "checked_positions": 0,
                    "missing_in_snapshot": [str(p.id) for p in open_positions],
                    "extra_in_snapshot": [],
                    "quantity_mismatches": [],
                    "warnings": warnings,
                },
            })
            return ReconciliationResult(
                job_run_id=job_run.id,
                reconciliation_report_id=report.id,
                reconciliation_type="positions_vs_valuations",
                scope_type="portfolio",
                scope_id=str(portfolio_id),
                status=report.status,
                differences_found=report.differences_found,
                warnings=warnings,
                metadata=report.metadata_,
            )

        val_ts = latest_pv.valuation_timestamp
        snap_positions = (
            db.query(PositionValuation)
            .filter(
                PositionValuation.portfolio_id == portfolio_id,
                PositionValuation.valuation_timestamp == val_ts,
            )
            .all()
        )

        current_ids = {str(p.id) for p in open_positions}
        snap_ids = {str(sv.position_id) for sv in snap_positions}

        missing_in_snap = sorted(current_ids - snap_ids)
        extra_in_snap = sorted(snap_ids - current_ids)

        snap_qty = {str(sv.position_id): Decimal(str(sv.quantity)) for sv in snap_positions}
        qty_mismatches = []
        for p in open_positions:
            pid = str(p.id)
            if pid in snap_qty:
                actual_q = Decimal(str(p.quantity))
                snap_q = snap_qty[pid]
                if actual_q != snap_q:
                    qty_mismatches.append({
                        "position_id": pid,
                        "current_quantity": str(actual_q),
                        "snapshot_quantity": str(snap_q),
                    })

        total_diffs = len(missing_in_snap) + len(extra_in_snap) + len(qty_mismatches)
        status = "matched" if total_diffs == 0 else "mismatched"

        meta = {
            "valuation_timestamp": str(val_ts),
            "checked_positions": len(current_ids),
            "missing_in_snapshot": missing_in_snap,
            "extra_in_snapshot": extra_in_snap,
            "quantity_mismatches": qty_mismatches,
        }

        report = _report_repo.create(db, data={
            "reconciliation_type": "positions_vs_valuations",
            "scope_type": "portfolio",
            "scope_id": str(portfolio_id),
            "status": status,
            "differences_found": total_diffs,
            "metadata_": meta,
        })

        return ReconciliationResult(
            job_run_id=job_run.id,
            reconciliation_report_id=report.id,
            reconciliation_type="positions_vs_valuations",
            scope_type="portfolio",
            scope_id=str(portfolio_id),
            status=status,
            differences_found=total_diffs,
            warnings=warnings,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # ledger_entries_vs_balances
    # ------------------------------------------------------------------

    def _reconcile_ledger_entries_vs_balances(
        self, db: Session, job_run: JobRun,
    ) -> ReconciliationResult:
        from ...ledger_accounts.models import LedgerAccount
        from ...ledger_entries.models import LedgerEntry

        accounts = db.query(LedgerAccount).all()

        entry_sums: dict[str, Decimal] = defaultdict(lambda: ZERO)
        entries = db.query(LedgerEntry).all()
        for e in entries:
            aid = str(e.account_id)
            amount = Decimal(str(e.amount))
            if e.entry_type == "debit":
                entry_sums[aid] += amount
            elif e.entry_type == "credit":
                entry_sums[aid] -= amount

        mismatches = []
        for acct in accounts:
            aid = str(acct.id)
            expected = entry_sums.get(aid, ZERO)
            actual = Decimal(str(acct.balance))
            if expected != actual:
                mismatches.append({
                    "account_id": aid,
                    "expected_balance": str(expected),
                    "actual_balance": str(actual),
                    "difference": str(actual - expected),
                })

        status = "matched" if not mismatches else "mismatched"
        meta = {
            "checked_accounts": len(accounts),
            "mismatches": mismatches,
        }

        report = _report_repo.create(db, data={
            "reconciliation_type": "ledger_entries_vs_balances",
            "scope_type": "global",
            "scope_id": None,
            "status": status,
            "differences_found": len(mismatches),
            "metadata_": meta,
        })

        return ReconciliationResult(
            job_run_id=job_run.id,
            reconciliation_report_id=report.id,
            reconciliation_type="ledger_entries_vs_balances",
            scope_type="global",
            status=status,
            differences_found=len(mismatches),
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # valuations_vs_performance
    # ------------------------------------------------------------------

    def _reconcile_valuations_vs_performance(
        self, db: Session, portfolio_id: UUID, job_run: JobRun,
    ) -> ReconciliationResult:
        from ...performance.models import PortfolioReturnSeries
        from ...valuations.models import PortfolioValuation

        val_snaps = (
            db.query(PortfolioValuation)
            .filter(PortfolioValuation.portfolio_id == portfolio_id)
            .order_by(PortfolioValuation.valuation_timestamp.asc())
            .all()
        )

        perf_rows = (
            db.query(PortfolioReturnSeries)
            .filter(PortfolioReturnSeries.portfolio_id == portfolio_id)
            .order_by(PortfolioReturnSeries.timestamp.asc())
            .all()
        )

        val_by_id = {str(v.id): v for v in val_snaps}
        missing_points = []
        nav_mismatches = []

        perf_val_ids = set()
        for pr in perf_rows:
            vid = str(pr.valuation_id) if pr.valuation_id else None
            if vid:
                perf_val_ids.add(vid)
                if vid in val_by_id:
                    val_nav = Decimal(str(val_by_id[vid].nav))
                    perf_nav = Decimal(str(pr.nav))
                    if val_nav != perf_nav:
                        nav_mismatches.append({
                            "valuation_id": vid,
                            "valuation_nav": str(val_nav),
                            "performance_nav": str(perf_nav),
                        })
                else:
                    missing_points.append({
                        "valuation_id": vid,
                        "issue": "performance row references missing valuation",
                    })

        total_diffs = len(missing_points) + len(nav_mismatches)
        status = "matched" if total_diffs == 0 else "mismatched"

        meta = {
            "valuation_points": len(val_snaps),
            "performance_points": len(perf_rows),
            "missing_points": missing_points,
            "nav_mismatches": nav_mismatches,
        }

        report = _report_repo.create(db, data={
            "reconciliation_type": "valuations_vs_performance",
            "scope_type": "portfolio",
            "scope_id": str(portfolio_id),
            "status": status,
            "differences_found": total_diffs,
            "metadata_": meta,
        })

        return ReconciliationResult(
            job_run_id=job_run.id,
            reconciliation_report_id=report.id,
            reconciliation_type="valuations_vs_performance",
            scope_type="portfolio",
            scope_id=str(portfolio_id),
            status=status,
            differences_found=total_diffs,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_portfolio(db: Session, portfolio_id: UUID) -> None:
        from ...portfolios.models import Portfolio
        exists = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if exists is None:
            raise PortfolioNotFoundForReconciliationError(portfolio_id)
