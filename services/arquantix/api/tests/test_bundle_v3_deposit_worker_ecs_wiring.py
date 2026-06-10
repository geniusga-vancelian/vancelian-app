"""Tests ECS wiring — Bundle V3 Deposit Worker dans defi_observability_tick.

Scénarios obligatoires (A–E) + intégration tick_service.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.defi_observability.tick_service import run_defi_observability_tick
from services.onchain_indexer.continuous_base_indexer import ContinuousIndexerRunResult
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    process_v3_deposit_rebalance_outbox_event,
    request_v3_bundle_deposit,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.worker import (
    process_bundle_v3_deposit_outbox,
)
from services.portfolio_engine.financial_operations.service import (
    find_active_portfolio_financial_operation,
)
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.test_bundle_v3_deposit_flow_pre_pr_gate import (
    _bundle_portfolio,
    _deposit_and_queue,
    _fund_patch,
    _seed_wallet_usdc,
    _usdc_instrument,
)


def _migrations_ready() -> bool:
    try:
        with engine.connect() as conn:
            for table in ("transaction_outbox", "portfolio_financial_operations"):
                row = conn.execute(
                    sa.text(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :t"
                    ),
                    {"t": table},
                ).fetchone()
                if row is None:
                    return False
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migrations_ready(),
    reason="Migrations 173+178 requises.",
)


@pytest.fixture
def ecs_env(monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_FLOW_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_IMMEDIATE_KICK_ENABLED", "false")
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED", "true")


@contextmanager
def _terminal_execute_patch(v3_status: str = "COMPLETED"):
    terminal = {
        "v3_status": v3_status,
        "rebalance_execution_id": str(uuid.uuid4()),
        "plan_hash": f"sha256:ecs-{uuid.uuid4().hex[:8]}",
        "resume_required": False,
    }
    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        return_value=terminal,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": "x"},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={
            "status": "ok",
            "plan_hash": terminal["plan_hash"],
            "buy_plan": [],
            "sell_plan": [],
        },
    ):
        yield terminal


def _mock_indexer_result(*, dry_run: bool) -> ContinuousIndexerRunResult:
    return ContinuousIndexerRunResult(
        chain_id=8453,
        dry_run=dry_run,
        enabled=True,
        status="completed",
        erc20={"inserted": 0, "skipped": 0},
        errors=[],
    )


def test_deposit_running_keeps_outbox_pending_for_worker_retry(db: Session, ecs_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, kings)
    outbox_rows = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    outbox = outbox_rows[0]
    outbox.locked_by = "test-worker"
    outbox.locked_at = datetime.now(timezone.utc)
    db.flush()

    running = {
        "v3_status": "RUNNING",
        "rebalance_execution_id": str(uuid.uuid4()),
        "batch_id": str(uuid.uuid4()),
        "plan_hash": "sha256:deposit-running",
        "resume_required": True,
    }
    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        return_value=running,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(kings.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={
            "status": "ok",
            "plan_hash": running["plan_hash"],
            "buy_plan": [],
            "sell_plan": [],
        },
    ):
        result = process_v3_deposit_rebalance_outbox_event(db, outbox=outbox)

    assert result["terminal"] is False
    assert result["awaiting_wallet_signature"] is True
    db.refresh(outbox)
    assert outbox.status == OutboxEventStatus.PENDING.value
    assert outbox.locked_by is None
    assert outbox.next_retry_at is not None


# ---------------------------------------------------------------------------
# A — outbox PENDING → worker → PROCESSED
# ---------------------------------------------------------------------------


def test_ecs_a_pending_to_processed(db: Session, ecs_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, kings)
    outbox_rows = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert len(outbox_rows) == 1
    assert outbox_rows[0].status == OutboxEventStatus.PENDING.value

    with _terminal_execute_patch():
        step = process_bundle_v3_deposit_outbox(db)

    assert step["enabled"] is True
    assert step["polled"] == 1
    assert step["processed"] == 1
    assert step["failed"] == 0

    db.expire_all()
    outbox_after = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox_after[0].status == OutboxEventStatus.PROCESSED.value
    assert find_active_portfolio_financial_operation(db, portfolio_id=kings.id) is None


# ---------------------------------------------------------------------------
# B — worker crash → outbox reste PENDING
# ---------------------------------------------------------------------------


def test_ecs_b_worker_crash_outbox_stays_pending(db: Session, ecs_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, kings)

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        side_effect=RuntimeError("simulated_worker_crash"),
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(kings.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "sha256:crash", "buy_plan": [], "sell_plan": []},
    ):
        step = process_bundle_v3_deposit_outbox(db)

    assert step["processed"] == 0
    assert step["failed"] == 1

    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox[0].status == OutboxEventStatus.PENDING.value
    assert find_active_portfolio_financial_operation(db, portfolio_id=kings.id) is not None


# ---------------------------------------------------------------------------
# C — worker restart → reprise idempotente
# ---------------------------------------------------------------------------


def test_ecs_c_worker_restart_idempotent(db: Session, ecs_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    fund_calls: list[str] = []
    execute_calls: list[str] = []
    crash_once = {"done": False}

    def _counting_fund(db, **kwargs):
        fund_calls.append("fund")
        return {"funded": True, "amount": "20"}

    def _execute_maybe_crash(db, **kwargs):
        execute_calls.append("execute")
        if not crash_once["done"]:
            crash_once["done"] = True
            raise RuntimeError("simulated_worker_crash")
        return {
            "v3_status": "COMPLETED",
            "rebalance_execution_id": str(uuid.uuid4()),
            "plan_hash": "sha256:restart",
            "resume_required": False,
        }

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        side_effect=_counting_fund,
    ):
        queued = request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=kings.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )

    assert len(fund_calls) == 1

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        side_effect=_execute_maybe_crash,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(kings.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "sha256:restart", "buy_plan": [], "sell_plan": []},
    ):
        step1 = process_bundle_v3_deposit_outbox(db)
        assert step1["failed"] == 1
        assert step1["processed"] == 0

        outbox = TransactionOutboxRepository.find_by_intent(
            db,
            uuid.UUID(queued["intent_id"]),
            event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        )
        outbox[0].next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.flush()

        step2 = process_bundle_v3_deposit_outbox(db)
        assert step2["processed"] == 1

    assert len(fund_calls) == 1
    assert len(execute_calls) == 2
    assert find_active_portfolio_financial_operation(db, portfolio_id=kings.id) is None


# ---------------------------------------------------------------------------
# D — 2 workers simultanés → aucun double traitement (SKIP LOCKED)
# ---------------------------------------------------------------------------


def test_ecs_d_two_workers_no_double_process(db: Session, ecs_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, kings)

    execute_calls: list[str] = []

    def _count_execute(db, **kwargs):
        execute_calls.append("execute")
        return {
            "v3_status": "COMPLETED",
            "rebalance_execution_id": str(uuid.uuid4()),
            "plan_hash": "sha256:concurrent",
            "resume_required": False,
        }

    rows1 = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        limit=10,
        locked_by="ecs-worker-1",
    )
    rows2 = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        limit=10,
        locked_by="ecs-worker-2",
    )
    assert len(rows1) == 1
    assert len(rows2) == 0

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        side_effect=_count_execute,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(kings.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={
            "status": "ok",
            "plan_hash": "sha256:concurrent",
            "buy_plan": [],
            "sell_plan": [],
        },
    ):
        result = process_v3_deposit_rebalance_outbox_event(db, outbox=rows1[0])
        assert result["terminal"] is True
        rows1[0].status = OutboxEventStatus.PROCESSED.value
        db.flush()

        step2 = process_bundle_v3_deposit_outbox(db)

    assert step2["polled"] == 0
    assert step2["processed"] == 0
    assert len(execute_calls) == 1

    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox[0].status == OutboxEventStatus.PROCESSED.value


# ---------------------------------------------------------------------------
# E — aucun événement V3 → coût nul
# ---------------------------------------------------------------------------


def test_ecs_e_no_v3_events_zero_cost(db: Session, ecs_env, monkeypatch):
    execute_calls: list[str] = []

    def _spy_execute(db, **kwargs):
        execute_calls.append("execute")
        return {"v3_status": "COMPLETED"}

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        side_effect=_spy_execute,
    ):
        step_on = process_bundle_v3_deposit_outbox(db)
        assert step_on["polled"] == 0
        assert step_on["processed"] == 0
        assert step_on["skipped"] is False
        assert execute_calls == []

        monkeypatch.delenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", raising=False)
        step_off = process_bundle_v3_deposit_outbox(db)
        assert step_off["skipped"] is True
        assert step_off["polled"] == 0
        assert execute_calls == []


# ---------------------------------------------------------------------------
# Intégration — step présent dans defi_observability_tick
# ---------------------------------------------------------------------------


@patch("services.defi_observability.tick_service.run_base_indexer_once")
@patch("services.defi_observability.tick_service.build_user_reconcile_report")
def test_ecs_tick_wires_bundle_v3_deposit_step(
    mock_user_reconcile,
    mock_indexer,
    db: Session,
    ecs_env,
):
    mock_indexer.return_value = _mock_indexer_result(dry_run=False)
    mock_user_reconcile.return_value = MagicMock(
        anomalies=[],
        discrepancies_written=0,
        warnings=[],
        to_dict=lambda: {},
    )

    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)
    _deposit_and_queue(db, pe, kings)

    with _terminal_execute_patch():
        summary = run_defi_observability_tick(
            db,
            dry_run=False,
            max_users=0,
            persist_job_run=False,
        )

    step = summary["steps"]["bundle_v3_deposit_outbox"]
    assert step["enabled"] is True
    assert step["processed"] == 1
    assert summary["bundle_v3_deposit_outbox"]["polled"] == 1


def test_ecs_tick_skips_when_worker_flag_off(db: Session, monkeypatch):
    monkeypatch.delenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", raising=False)

    with patch("services.defi_observability.tick_service.run_base_indexer_once") as mock_indexer, patch(
        "services.defi_observability.tick_service.build_user_reconcile_report"
    ) as mock_user_reconcile:
        mock_indexer.return_value = _mock_indexer_result(dry_run=False)
        mock_user_reconcile.return_value = MagicMock(
            anomalies=[],
            discrepancies_written=0,
            warnings=[],
            to_dict=lambda: {},
        )
        summary = run_defi_observability_tick(
            db,
            dry_run=False,
            max_users=0,
            persist_job_run=False,
        )

    step = summary["steps"]["bundle_v3_deposit_outbox"]
    assert step["skipped"] is True
    assert step["enabled"] is False
