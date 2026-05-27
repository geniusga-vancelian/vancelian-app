"""Tests Phase 10 — lock, timeout, prod readiness."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from services.defi_observability.job_run_repository import DefiJobRunRepository
from services.defi_observability.lock import (
    release_defi_tick_lock,
    try_acquire_defi_tick_lock,
)
from services.defi_observability.models import DefiObservabilityJobRun
from services.defi_observability.tick_service import (
    record_skipped_locked_tick,
    run_defi_observability_tick,
)
from services.onchain_indexer.continuous_base_indexer import ContinuousIndexerRunResult
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from tests.test_phase9_defi_observability_tick import (
    _migration_168_ready,
    _mock_indexer_result,
)
from tests.test_phase7_transaction_intents import _migration_166_ready


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_168_ready(), reason="Migration 168 requise."),
]


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


@pytest.mark.skipif(not _is_postgres(), reason="Advisory lock PostgreSQL requis.")
def test_advisory_lock_second_acquire_fails(db: Session):
    assert try_acquire_defi_tick_lock(db) is True
    db2 = SessionLocal()
    try:
        assert try_acquire_defi_tick_lock(db2) is False
    finally:
        db2.close()
        release_defi_tick_lock(db)


@pytest.mark.skipif(not _is_postgres(), reason="Advisory lock PostgreSQL requis.")
def test_skipped_locked_job_run(db: Session):
    assert try_acquire_defi_tick_lock(db)
    db2 = SessionLocal()
    try:
        summary = record_skipped_locked_tick(db2, persist_job_run=True)
        db2.commit()
        assert summary["overall_status"] == "skipped_locked"
        row = DefiJobRunRepository.find_by_id(db2, uuid.UUID(summary["job_run_id"]))
        assert row is not None
        assert row.status == "skipped_locked"
    finally:
        db2.close()
        release_defi_tick_lock(db)
        db.rollback()


@pytest.mark.skipif(not _is_postgres(), reason="Advisory lock PostgreSQL requis.")
@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_lock_released_after_success(
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
    assert try_acquire_defi_tick_lock(db)
    try:
        run_defi_observability_tick(db, dry_run=False, max_users=0, persist_job_run=False)
    finally:
        release_defi_tick_lock(db)

    db2 = SessionLocal()
    try:
        assert try_acquire_defi_tick_lock(db2) is True
        release_defi_tick_lock(db2)
        db2.commit()
    finally:
        db2.close()
    db.rollback()


@pytest.mark.skipif(not _is_postgres(), reason="Advisory lock PostgreSQL requis.")
@patch("services.defi_observability.tick_service.run_base_indexer_once")
def test_lock_released_after_exception(mock_indexer, db: Session):
    mock_indexer.return_value = _mock_indexer_result(dry_run=False)
    assert try_acquire_defi_tick_lock(db)
    try:
        with patch.object(
            DefiJobRunRepository,
            "finish",
            side_effect=RuntimeError("persist failed"),
        ):
            with pytest.raises(RuntimeError):
                run_defi_observability_tick(
                    db,
                    dry_run=False,
                    max_users=0,
                    persist_job_run=True,
                )
    finally:
        release_defi_tick_lock(db)

    db2 = SessionLocal()
    try:
        assert try_acquire_defi_tick_lock(db2) is True
        release_defi_tick_lock(db2)
        db2.commit()
    finally:
        db2.close()
    db.rollback()


@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_max_duration_timeout_degraded(
    mock_user_reconcile,
    mock_indexer,
    db: Session,
    monkeypatch,
):
    mock_indexer.return_value = _mock_indexer_result(dry_run=True)
    mock_user_reconcile.return_value = MagicMock(
        anomalies=[],
        discrepancies_written=0,
        warnings=[],
        to_dict=lambda: {},
    )
    t = {"v": 0.0}

    def fake_monotonic() -> float:
        t["v"] += 100.0
        return t["v"]

    summary = run_defi_observability_tick(
        db,
        dry_run=True,
        max_users=2,
        persist_job_run=False,
        max_duration_seconds=1,
        monotonic=fake_monotonic,
    )
    db.rollback()

    assert summary["overall_status"] == "timeout_degraded"
    assert summary.get("timeout") is True
    mock_indexer.assert_not_called()


@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_timeout_after_indexer_skips_user_reconcile(
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
    call = {"n": 0}

    def mono() -> float:
        call["n"] += 1
        return 0.0 if call["n"] <= 3 else 100.0

    summary = run_defi_observability_tick(
        db,
        dry_run=True,
        max_users=1,
        persist_job_run=False,
        max_duration_seconds=1,
        monotonic=mono,
    )
    db.rollback()

    assert summary["overall_status"] == "timeout_degraded"
    assert "indexer" in summary
    assert summary.get("stopped_before_step", "").startswith("user_reconcile")
    mock_user_reconcile.assert_not_called()


def test_no_balance_modification_phase10(db: Session, monkeypatch):
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())

    with patch("services.defi_observability.tick_service.run_base_indexer_once") as mock_idx:
        mock_idx.return_value = _mock_indexer_result(dry_run=True)
        run_defi_observability_tick(
            db,
            dry_run=True,
            max_users=0,
            persist_job_run=False,
            max_duration_seconds=9999,
        )

    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


@patch("services.defi_observability.tick_service.run_base_indexer_once")
def test_timeout_job_run_status(mock_indexer, db: Session):
    mock_indexer.return_value = _mock_indexer_result(dry_run=False)
    t = {"v": 0.0}

    def fake_monotonic() -> float:
        t["v"] += 50.0
        return t["v"]

    summary = run_defi_observability_tick(
        db,
        dry_run=False,
        max_users=0,
        persist_job_run=True,
        max_duration_seconds=1,
        monotonic=fake_monotonic,
    )
    db.commit()

    assert summary["overall_status"] == "timeout_degraded"
    row = DefiJobRunRepository.find_by_id(db, uuid.UUID(summary["job_run_id"]))
    assert row is not None
    assert row.status == "timeout_degraded"
