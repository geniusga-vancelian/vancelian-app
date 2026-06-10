"""Tests Bundle V3 Rebalancing Executor — PR-3."""
from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.types import ExecutionLeg, ExecutionResult
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from datetime import datetime, timedelta, timezone

from services.lifi.enums import SwapSessionStatus
from services.portfolio_engine.bundles.rebalance_executor import (
    ACTION_V3_PROGRESS,
    ACTION_V3_RUNNING,
    ACTION_V3_TERMINAL,
    ENTITY_TYPE_V3_REBALANCE,
    BundleRebalanceExecutor,
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
    find_running_v3_rebalance_execution,
    find_terminal_v3_rebalance_by_plan_hash,
    reconcile_running_v3_rebalance_execution,
    terminalize_stale_v3_rebalance_execution,
)
from services.portfolio_engine.bundles.rebalance_planner import (
    plan_bundle_rebalance_from_drift,
)
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext

from conftest import make_linked_client, mobile_auth_headers
from tests.test_bundle_allocation_phase5a import (
    _bundle_with_allocations,
    _instrument_for_asset,
)
from tests.test_bundle_drift_engine import _FixedPriceResolver, _credit_cash, _credit_spot
from tests.test_bundle_rebalance_planner import (
    _majors_prices,
    _majors_weights,
    _seed_majors_spot,
)


class _RecordingMockProvider:
    """Mock execution — enregistre l'ordre des legs sans écriture PE."""

    name = "mock_v3"

    def __init__(
        self,
        *,
        outcomes: dict[str, list[str]] | None = None,
        default_status: str = "completed",
    ):
        self.calls: list[dict] = []
        self._outcomes = outcomes or {}
        self._default = default_status
        self._attempt_counts: dict[str, int] = {}

    def quote_leg(self, db, leg):
        raise NotImplementedError

    def execute_leg(self, db, leg: ExecutionLeg, actor) -> ExecutionResult:
        self.calls.append({
            "leg_id": leg.leg_id,
            "action": leg.action,
            "from_asset": leg.from_asset,
            "to_asset": leg.to_asset,
            "amount_from": leg.amount_from,
            "batch_id": leg.batch_id,
        })
        key = f"{leg.action}:{leg.metadata.get('target_instrument_id', leg.to_asset)}"
        attempts = self._attempt_counts.get(key, 0) + 1
        self._attempt_counts[key] = attempts

        outcome_list = self._outcomes.get(key) or self._outcomes.get(leg.action)
        if outcome_list:
            idx = min(attempts - 1, len(outcome_list) - 1)
            status = outcome_list[idx]
        else:
            status = self._default

        if status == "raise":
            raise RuntimeError(f"mock_fail:{leg.leg_id}")

        raw: dict = {"mock": True}
        if status == "pending":
            raw["requires_client_signature"] = True
        return ExecutionResult(
            leg_id=leg.leg_id,
            status=status,  # type: ignore[arg-type]
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            amount_to=leg.amount_from,
            provider_order_id=f"mock-swap-{leg.leg_id}",
            raw=raw,
        )


def _adapter(provider: _RecordingMockProvider) -> BundleExecutionAdapter:
    adapter = BundleExecutionAdapter.__new__(BundleExecutionAdapter)
    adapter._provider = provider
    return adapter


def _pe_cb_counts(db: Session) -> tuple[int, int]:
    pe = int(db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar() or 0)
    cb = int(db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar() or 0)
    return pe, cb


def _majors_plan(db: Session, pe, portfolio, usdc) -> dict:
    resolver = _FixedPriceResolver(_majors_prices())
    _seed_majors_spot(db, portfolio.id)
    _credit_cash(db, portfolio.id, usdc.id, "29.866638")
    db.commit()
    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    return plan_bundle_rebalance_from_drift(snap)


def _kings_plan(db: Session, pe, portfolio, usdc) -> dict:
    resolver = _FixedPriceResolver({
        "USDC": Decimal("0.92"),
        "BTC": Decimal("95000"),
        "ETH": Decimal("3200"),
    })
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.0004250000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.0023810000")
    _credit_cash(db, portfolio.id, usdc.id, "30.900000")
    db.commit()
    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    return plan_bundle_rebalance_from_drift(snap)


def test_majors_buy_only_eth_uni_no_btc_sell(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    assert plan["sell_plan"] == []

    provider = _RecordingMockProvider()
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "COMPLETED"
    assert result["resume_required"] is False
    buy_assets = {r["asset"] for r in result["buy_results"]}
    assert buy_assets == {"ETH", "UNI"}
    assert "BTC" not in {c["from_asset"] for c in provider.calls}
    assert all(c["action"] == "rebalance_buy" for c in provider.calls)


def test_kings_buy_only_eth_no_btc_sell(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
    )
    plan = _kings_plan(db, pe, portfolio, usdc)
    assert plan["sell_plan"] == []

    provider = _RecordingMockProvider()
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "COMPLETED"
    assert len(result["buy_results"]) == 1
    assert result["buy_results"][0]["asset"] == "ETH"
    assert not any(c["from_asset"] == "BTC" for c in provider.calls)


def test_sell_then_buy_order(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    resolver = _FixedPriceResolver(
        {"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")},
    )
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.02")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.001")
    db.commit()
    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan = plan_bundle_rebalance_from_drift(snap)
    assert plan["sell_plan"]
    assert plan["buy_plan"]

    provider = _RecordingMockProvider()
    exchange = MagicMock()
    exchange._resolve_price = MagicMock(
        side_effect=lambda _db, asset, override_price=None, side="sell": {
            "USDC": Decimal("0.92"),
            "BTC": Decimal("90000"),
            "ETH": Decimal("3000"),
        }[asset.upper()]
    )
    executor = BundleRebalanceExecutor(
        execution_adapter=_adapter(provider),
        exchange_service=exchange,
    )
    result = executor.execute_drift_rebalance_plan(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
    )
    db.commit()

    actions = [c["action"] for c in provider.calls]
    first_buy = actions.index("rebalance_buy")
    last_sell = len(actions) - 1 - actions[::-1].index("rebalance_sell")
    assert first_buy > last_sell


def test_max_swap_attempts_two_no_third(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    plan = {
        "status": "ok",
        "plan_hash": "sha256:test-attempts",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "weight_basis": "invested_assets",
        "cash_funding_source": "separate",
        "available_cash_usdc": "10",
        "sell_plan": [],
        "buy_plan": [{
            "asset": "ETH",
            "instrument_id": str(_instrument_for_asset(db, "ETH").id),
            "amount_usdc": "5",
            "action": "buy",
            "funded_by": "cash_leg",
        }],
    }
    provider = _RecordingMockProvider(
        outcomes={"rebalance_buy": ["raise", "raise", "completed"]},
    )
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
        execution_adapter=_adapter(provider),
    )
    db.commit()

    eth_calls = [c for c in provider.calls if c["action"] == "rebalance_buy"]
    assert len(eth_calls) == 2
    assert result["buy_results"][0]["attempts"] == 2
    assert result["resume_required"] is False


def test_timeout_pending_becomes_terminal_no_resume(db: Session, monkeypatch):
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)

    provider = _RecordingMockProvider(default_status="pending")
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        trigger="cron",
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "COMPLETED_WITH_RESIDUAL_CASH"
    assert result["resume_required"] is False
    assert all(r["status"] == "expired" for r in result["buy_results"])
    assert all(r["attempts"] == 2 for r in result["buy_results"])
    buy_calls = [c for c in provider.calls if c["action"] == "rebalance_buy"]
    assert len(buy_calls) == len(result["buy_results"]) * 2


def test_manual_trigger_returns_running_with_pending_swap(db: Session, monkeypatch):
    """manual/deposit : quote leg → RUNNING + pending (pas d'expiration immédiate)."""
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = {
        "status": "ok",
        "plan_hash": f"sha256:manual-pending-{uuid.uuid4().hex[:8]}",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "available_cash_usdc": "10",
        "sell_plan": [],
        "buy_plan": [{
            "asset": "ETH",
            "instrument_id": str(_instrument_for_asset(db, "ETH").id),
            "amount_usdc": "5",
            "action": "buy",
            "funded_by": "cash_leg",
        }],
    }
    provider = _RecordingMockProvider(default_status="pending")
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        trigger="manual",
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "RUNNING"
    assert result["resume_required"] is True
    assert result["client_signature_required"] is True
    assert len(result["buy_results"]) == 1
    assert result["buy_results"][0]["status"] == "pending"
    assert result["buy_results"][0]["swap_id"]
    assert len(provider.calls) == 1


def test_quote_ttl_expired_retry_success_on_attempt2(db: Session, monkeypatch):
    """attempt 1 quote_ttl_expired → re-quote → attempt 2 success → COMPLETED."""
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = {
        "status": "ok",
        "plan_hash": f"sha256:ttl-retry-{uuid.uuid4().hex[:8]}",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "weight_basis": "invested_assets",
        "cash_funding_source": "separate",
        "available_cash_usdc": "10",
        "sell_plan": [],
        "buy_plan": [{
            "asset": "ETH",
            "instrument_id": str(_instrument_for_asset(db, "ETH").id),
            "amount_usdc": "5",
            "action": "buy",
            "funded_by": "cash_leg",
        }],
    }
    provider = _RecordingMockProvider(
        outcomes={"rebalance_buy": ["pending", "completed"]},
    )
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        trigger="cron",
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "COMPLETED"
    assert result["buy_results"][0]["attempts"] == 2
    assert result["buy_results"][0]["status"] == "completed"
    details = result["buy_results"][0]["attempt_details"]
    assert len(details) == 2
    assert details[0]["error_code"] == "quote_ttl_expired"
    assert details[1]["status"] == "completed"
    assert len(provider.calls) == 2


def test_quote_ttl_expired_both_attempts_terminal_residual(db: Session, monkeypatch):
    """attempt 1 + 2 quote_ttl_expired → COMPLETED_WITH_RESIDUAL_CASH, attempts never > 2."""
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = {
        "status": "ok",
        "plan_hash": f"sha256:ttl-fail2-{uuid.uuid4().hex[:8]}",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "available_cash_usdc": "5",
        "sell_plan": [],
        "buy_plan": [{
            "asset": "ETH",
            "instrument_id": str(_instrument_for_asset(db, "ETH").id),
            "amount_usdc": "5",
            "action": "buy",
            "funded_by": "cash_leg",
        }],
    }
    provider = _RecordingMockProvider(default_status="pending")
    pe_before, cb_before = _pe_cb_counts(db)
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        trigger="cron",
        execution_adapter=_adapter(provider),
    )
    db.commit()
    pe_after, cb_after = _pe_cb_counts(db)

    assert result["v3_status"] == "COMPLETED_WITH_RESIDUAL_CASH"
    assert result["buy_results"][0]["attempts"] == 2
    assert result["buy_results"][0]["error"] == "quote_ttl_expired"
    assert len(provider.calls) == 2
    assert pe_after == pe_before
    assert cb_after == cb_before


def test_idempotency_running_same_plan_hash(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())

    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_RUNNING,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "sell_plan": [],
            "buy_plan": plan["buy_plan"],
        },
    )
    db.commit()

    found = find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id))
    assert found is not None
    assert found["plan_hash"] == plan["plan_hash"]

    provider = _RecordingMockProvider()
    result = BundleRebalanceExecutor(
        execution_adapter=_adapter(provider),
    ).execute_drift_rebalance_plan(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
    )
    assert result["rebalance_execution_id"] == execution_id
    assert len(provider.calls) > 0
    calls_after_resume = len(provider.calls)
    db.flush()

    replay = BundleRebalanceExecutor(
        execution_adapter=_adapter(provider),
    ).execute_drift_rebalance_plan(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
    )
    assert replay["rebalance_execution_id"] == execution_id
    assert len(provider.calls) == calls_after_resume


def test_plan_hash_mismatch_terminalizes_running_and_starts_new(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())

    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_RUNNING,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "sell_plan": [],
            "buy_plan": plan["buy_plan"],
        },
    )
    db.commit()

    provider = _RecordingMockProvider()
    other_plan = dict(plan)
    other_plan["plan_hash"] = "sha256:other-plan"
    other_result = BundleRebalanceExecutor(
        execution_adapter=_adapter(provider),
    ).execute_drift_rebalance_plan(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=other_plan,
        plan_hash=other_plan["plan_hash"],
    )
    assert other_result["rebalance_execution_id"] != execution_id
    assert other_result["plan_hash"] == "sha256:other-plan"
    assert find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id)) is None


def test_no_side_effects_while_pending(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)

    pe_before, cb_before = _pe_cb_counts(db)
    provider = _RecordingMockProvider(default_status="pending")
    execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()
    pe_after, cb_after = _pe_cb_counts(db)
    assert pe_after == pe_before
    assert cb_after == cb_before


def test_completed_with_residual_cash(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    eth_id = str(_instrument_for_asset(db, "ETH").id)
    uni_id = str(_instrument_for_asset(db, "UNI").id)

    provider = _RecordingMockProvider(
        outcomes={
            f"rebalance_buy:{eth_id}": ["completed"],
            f"rebalance_buy:{uni_id}": ["raise", "raise"],
        },
    )
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] == "COMPLETED_WITH_RESIDUAL_CASH"
    assert result["cash_remaining_usdc"] is not None
    assert result["resume_required"] is False


def test_no_legacy_resume_import_in_executor_module():
    src = Path(
        "services/portfolio_engine/bundles/rebalance_executor.py",
    ).read_text(encoding="utf-8")
    assert "resume_lifi_invest_batch(" not in src
    assert ".resume_lifi_invest_batch" not in src


def test_empty_sell_plan_skips_sells(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)

    provider = _RecordingMockProvider()
    execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()
    assert not any(c["action"] == "rebalance_sell" for c in provider.calls)


def test_stale_running_terminalized_not_indefinite(db: Session, monkeypatch):
    monkeypatch.setenv("MAX_EXECUTION_AGE_MINUTES", "5")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())
    stale_start = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_RUNNING,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "started_at": stale_start,
            "available_cash_usdc": plan["available_cash_usdc"],
            "sell_results": [],
            "buy_results": [{"asset": "ETH", "status": "pending", "attempts": 1}],
        },
    )
    db.commit()

    import importlib
    import services.portfolio_engine.bundles.rebalance_executor as rex

    importlib.reload(rex)
    terminal = rex.terminalize_stale_v3_rebalance_execution(
        db, portfolio_id=str(portfolio.id),
    )
    db.commit()

    assert terminal is not None
    assert terminal["v3_status"] in ("COMPLETED_WITH_RESIDUAL_CASH", "FAILED")
    assert terminal.get("stale_terminalized") is True
    assert rex.find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id)) is None


def test_crash_resume_same_execution_no_duplicate_swaps(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())

    eth_leg = next(b for b in plan["buy_plan"] if b["asset"] == "ETH")
    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_PROGRESS,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "available_cash_usdc": plan["available_cash_usdc"],
            "sell_results": [],
            "buy_results": [{
                "asset": "ETH",
                "instrument_id": eth_leg["instrument_id"],
                "action": "buy",
                "amount_usdc": eth_leg["amount_usdc"],
                "status": "completed",
                "attempts": 1,
                "leg_ids": ["v3-rebal-crash-eth-a1"],
            }],
        },
    )
    db.commit()

    provider = _RecordingMockProvider()
    result = BundleRebalanceExecutor(
        execution_adapter=_adapter(provider),
    ).execute_drift_rebalance_plan(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
    )
    db.commit()

    assert result["rebalance_execution_id"] == execution_id
    assert result["batch_id"] == execution_id
    eth_calls = [c for c in provider.calls if c["action"] == "rebalance_buy" and "ETH" in c["leg_id"]]
    assert eth_calls == []
    assert any(c["action"] == "rebalance_buy" for c in provider.calls)


def test_expired_eth_only_residual_cash_not_failed(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    eth_id = str(_instrument_for_asset(db, "ETH").id)

    provider = _RecordingMockProvider(
        outcomes={f"rebalance_buy:{eth_id}": ["raise", "raise"]},
    )
    plan_one_leg = dict(plan)
    plan_one_leg["buy_plan"] = [b for b in plan["buy_plan"] if b["asset"] == "ETH"]
    plan_one_leg["sell_plan"] = []

    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan_one_leg,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["buy_results"][0]["status"] == "failed"
    assert result["v3_status"] == "COMPLETED_WITH_RESIDUAL_CASH"


def test_triple_execute_same_plan_one_batch(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    provider = _RecordingMockProvider()

    r1 = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.flush()
    calls_after_first = len(provider.calls)

    r2 = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    r3 = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert r1["rebalance_execution_id"] is not None
    assert r2["rebalance_execution_id"] == r1["rebalance_execution_id"]
    assert r3["rebalance_execution_id"] == r1["rebalance_execution_id"]
    assert len(provider.calls) == calls_after_first
    assert find_terminal_v3_rebalance_by_plan_hash(
        db, portfolio_id=str(portfolio.id), plan_hash=plan["plan_hash"],
    ) is not None


def test_terminal_audit_written(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)

    provider = _RecordingMockProvider()
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    terminal = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_TERMINAL,
            AuditEvent.entity_id == result["rebalance_execution_id"],
        )
        .first()
    )
    assert terminal is not None
    assert find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id)) is None


def _v3_running_audit_count(db: Session) -> int:
    return int(
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action == ACTION_V3_RUNNING,
        )
        .count()
        or 0
    )


@pytest.mark.parametrize(
    "flag_value",
    [pytest.param(None, id="absent"), pytest.param("false", id="false")],
)
def test_v3_execute_route_flag_off_returns_404_no_side_effects(
    client,
    db: Session,
    monkeypatch,
    flag_value: str | None,
):
    """Route V3 inactive par défaut — 404 sans audit, batch, swap ni écriture PE/CB."""
    if flag_value is None:
        monkeypatch.delenv("BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED", raising=False)
    else:
        monkeypatch.setenv("BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED", flag_value)

    pe = make_linked_client(db)
    portfolio, _usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    db.commit()

    pe_before, cb_before = _pe_cb_counts(db)
    audit_before = _v3_running_audit_count(db)
    swap_before = int(db.query(PersonWalletSwap).count() or 0)

    response = client.post(
        f"/api/app/bundle/{portfolio.id}/rebalance/v3/execute",
        headers=mobile_auth_headers(db, pe),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "v3_executor_disabled"

    pe_after, cb_after = _pe_cb_counts(db)
    assert pe_after == pe_before
    assert cb_after == cb_before
    assert _v3_running_audit_count(db) == audit_before
    assert int(db.query(PersonWalletSwap).count() or 0) == swap_before


def test_reconcile_completed_legs_terminalizes(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())

    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_PROGRESS,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "trigger": "manual",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "available_cash_usdc": plan["available_cash_usdc"],
            "sell_results": [],
            "buy_results": [{
                "asset": "ETH",
                "instrument_id": str(_instrument_for_asset(db, "ETH").id),
                "action": "buy",
                "amount_usdc": "5",
                "status": "completed",
                "attempts": 1,
                "leg_ids": ["v3-rebal-done-eth-a1"],
            }],
        },
    )
    db.commit()

    terminal = reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=str(portfolio.id),
        client_id=pe.id,
        drift_rebalance_plan=plan,
        auto_progress=False,
    )
    db.commit()

    assert terminal is not None
    assert terminal["v3_status"] in ("COMPLETED", "COMPLETED_WITH_RESIDUAL_CASH")
    assert terminal.get("reconciled_terminalized") is True
    assert find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id)) is None


def test_reconcile_expired_swap_pending_terminalizes(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)
    execution_id = str(uuid.uuid4())
    swap_id = uuid.uuid4()

    db.add(
        PersonWalletSwap(
            id=swap_id,
            person_id=pe.person_id,
            from_asset="AAVE",
            to_asset="USDC",
            from_chain="base",
            to_chain="base",
            amount_in=Decimal("1"),
            estimated_receive=Decimal("4"),
            status=SwapSessionStatus.EXPIRED.value,
            audit_log=[],
        ),
    )
    db.flush()

    AuditService.log_event(
        db,
        entity_type=ENTITY_TYPE_V3_REBALANCE,
        entity_id=execution_id,
        action=ACTION_V3_PROGRESS,
        metadata={
            "rebalance_execution_id": execution_id,
            "batch_id": execution_id,
            "portfolio_id": str(portfolio.id),
            "plan_hash": plan["plan_hash"],
            "v3_status": "RUNNING",
            "trigger": "manual",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "available_cash_usdc": plan["available_cash_usdc"],
            "sell_results": [{
                "asset": "AAVE",
                "instrument_id": str(_instrument_for_asset(db, "AAVE").id),
                "action": "sell",
                "amount_usdc": "4",
                "status": "pending",
                "attempts": 1,
                "leg_ids": ["v3-rebal-exp-aave-a1"],
                "swap_id": str(swap_id),
                "error": "awaiting_client_signature",
            }],
            "buy_results": [],
        },
    )
    db.commit()

    terminal = reconcile_running_v3_rebalance_execution(
        db,
        portfolio_id=str(portfolio.id),
        client_id=pe.id,
        drift_rebalance_plan=plan,
        auto_progress=False,
    )
    db.commit()

    assert terminal is not None
    assert terminal["v3_status"] in ("COMPLETED_WITH_RESIDUAL_CASH", "FAILED")
    assert find_running_v3_rebalance_execution(db, portfolio_id=str(portfolio.id)) is None
