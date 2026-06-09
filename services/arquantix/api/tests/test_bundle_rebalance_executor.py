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
from services.portfolio_engine.bundles.rebalance_executor import (
    ACTION_V3_RUNNING,
    ACTION_V3_TERMINAL,
    ENTITY_TYPE_V3_REBALANCE,
    BundleRebalanceExecutor,
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
    find_running_v3_rebalance_execution,
)
from services.portfolio_engine.bundles.rebalance_planner import (
    plan_bundle_rebalance_from_drift,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext

from conftest import make_linked_client
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

        return ExecutionResult(
            leg_id=leg.leg_id,
            status=status,  # type: ignore[arg-type]
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            amount_to=leg.amount_from,
            provider_order_id=f"mock-swap-{leg.leg_id}",
            raw={"mock": True},
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


def test_timeout_pending_becomes_terminal_no_resume(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    plan = _majors_plan(db, pe, portfolio, usdc)

    provider = _RecordingMockProvider(default_status="pending")
    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        execution_adapter=_adapter(provider),
    )
    db.commit()

    assert result["v3_status"] in ("FAILED", "COMPLETED_WITH_RESIDUAL_CASH")
    assert result["resume_required"] is False
    assert all(r["status"] == "expired" for r in result["buy_results"])


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
    assert provider.calls == []

    other_plan = dict(plan)
    other_plan["plan_hash"] = "sha256:other-plan"
    with pytest.raises(BundleRebalanceExecutorError, match="portfolio_has_running"):
        BundleRebalanceExecutor(
            execution_adapter=_adapter(provider),
        ).execute_drift_rebalance_plan(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            drift_rebalance_plan=other_plan,
            plan_hash=other_plan["plan_hash"],
        )


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
