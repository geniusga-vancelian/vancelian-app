"""Tests Phase 9 — defi_observability_tick."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.defi_observability.job_run_repository import DefiJobRunRepository
from services.defi_observability.models import DefiObservabilityJobRun
from services.defi_observability.tick_service import run_defi_observability_tick
from services.onchain_indexer.continuous_base_indexer import ContinuousIndexerRunResult
from services.onchain_indexer.models import TransactionIntent
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentStatus
from services.transaction_intents.repository import TransactionIntentRepository
from tests.conftest import make_linked_client
from tests.test_phase7_transaction_intents import _migration_166_ready


def _migration_168_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'defi_observability_job_runs'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_168_ready(), reason="Migration 168 requise."),
]


def _mock_indexer_result(*, dry_run: bool, errors: list | None = None) -> ContinuousIndexerRunResult:
    return ContinuousIndexerRunResult(
        chain_id=8453,
        dry_run=dry_run,
        enabled=True,
        status="completed",
        erc20={"inserted": 2, "skipped": 0},
        errors=errors or [],
    )


@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_tick_dry_run_writes_nothing(
    mock_user_reconcile,
    mock_indexer,
    db: Session,
):
    mock_indexer.return_value = _mock_indexer_result(dry_run=True)
    mock_user_reconcile.return_value = MagicMock(
        anomalies=[],
        discrepancies_written=0,
        warnings=[],
        to_dict=lambda: {},
    )

    before_jobs = db.query(DefiObservabilityJobRun).count()
    before_disc = db.query(ReconciliationDiscrepancy).count()

    summary = run_defi_observability_tick(db, dry_run=True, max_users=0, persist_job_run=True)
    db.rollback()

    assert summary["dry_run"] is True
    assert summary["overall_status"] in ("success", "degraded")
    assert db.query(DefiObservabilityJobRun).count() == before_jobs
    assert db.query(ReconciliationDiscrepancy).count() == before_disc
    mock_indexer.assert_called_once()
    assert mock_indexer.call_args.kwargs.get("dry_run") is True


@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_tick_no_dry_run_writes_job_run_only_when_committed(
    mock_user_reconcile,
    mock_indexer,
    db: Session,
):
    mock_indexer.return_value = _mock_indexer_result(dry_run=False)
    mock_user_reconcile.return_value = MagicMock(
        anomalies=[],
        discrepancies_written=0,
        warnings=[],
        to_dict=lambda: {},
    )

    summary = run_defi_observability_tick(db, dry_run=False, max_users=0, persist_job_run=True)
    db.commit()

    assert summary.get("job_run_id")
    row = DefiJobRunRepository.find_by_id(db, uuid.UUID(summary["job_run_id"]))
    assert row is not None
    assert row.status in ("success", "degraded")


@patch("services.defi_observability.tick_service.run_base_indexer_once")
def test_indexer_error_still_produces_degraded_health(mock_indexer, db: Session):
    mock_indexer.return_value = _mock_indexer_result(dry_run=True, errors=["rpc timeout"])

    summary = run_defi_observability_tick(db, dry_run=True, max_users=0, persist_job_run=False)
    db.rollback()

    assert summary["overall_status"] == "degraded"
    assert "health" in summary
    assert summary["health"].get("by_product") is not None or "global" in summary.get("health", {})


@patch("services.defi_observability.tick_service.run_base_indexer_once")
def test_indexer_step_exception_allows_health(mock_indexer, db: Session):
    mock_indexer.side_effect = RuntimeError("indexer down")

    summary = run_defi_observability_tick(db, dry_run=True, max_users=0, persist_job_run=False)
    db.rollback()

    assert summary["overall_status"] == "degraded"
    assert "health" in summary
    assert summary["indexer"].get("error")


def test_no_balance_modification(db: Session, monkeypatch):
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())

    with patch("services.defi_observability.tick_service.run_base_indexer_once") as mock_idx:
        mock_idx.return_value = _mock_indexer_result(dry_run=True)
        run_defi_observability_tick(db, dry_run=True, max_users=0, persist_job_run=False)

    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


def test_stale_p1_alert_in_summary(db: Session):
    pe = make_linked_client(db)
    old = datetime.now(timezone.utc) - timedelta(hours=5)
    row, _ = TransactionIntentRepository.upsert(
        db,
        person_id=pe.person_id,
        product_type="lombard_borrow",
        operation_type="borrow",
        idempotency_key=f"stale-p1-{uuid.uuid4().hex[:8]}",
        status=IntentStatus.AWAITING_SIGNATURE.value,
        wallet_address="0xabc",
    )
    row.updated_at = old
    row.created_at = old
    db.add(row)
    db.commit()

    with patch("services.defi_observability.tick_service.run_base_indexer_once") as mock_idx:
        mock_idx.return_value = _mock_indexer_result(dry_run=True)
        summary = run_defi_observability_tick(db, dry_run=True, max_users=0, persist_job_run=False)
    db.rollback()

    codes = [a.get("code") for a in summary.get("alerts", [])]
    assert "stale_intent_p1" in codes
