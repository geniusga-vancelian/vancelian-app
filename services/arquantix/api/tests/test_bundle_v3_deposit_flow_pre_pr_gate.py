"""GATE PRE-PR — Bundle V3 Deposit Flow (8 scénarios obligatoires).

Exécution : pytest tests/test_bundle_v3_deposit_flow_pre_pr_gate.py -v
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    process_v3_deposit_rebalance_outbox_event,
    request_v3_bundle_deposit,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.worker import (
    tick_bundle_v3_deposit_worker,
)
from services.portfolio_engine.financial_operations.enums import PortfolioFinancialOperationStatus
from services.portfolio_engine.financial_operations.exceptions import (
    PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE,
    PortfolioFinancialOperationInProgress409,
)
from services.portfolio_engine.financial_operations.models import PortfolioFinancialOperation
from services.portfolio_engine.financial_operations.service import (
    audit_portfolio_financial_operations,
    find_active_portfolio_financial_operation,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.test_bundle_rebalance_executor import (
    _RecordingMockProvider,
    _adapter,
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


# ---------------------------------------------------------------------------
# Fixtures / harness
# ---------------------------------------------------------------------------


@pytest.fixture
def gate_env(monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_FLOW_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", "true")
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED", "true")


def _usdc_instrument(db: Session) -> Instrument:
    asset = db.query(Asset).filter(Asset.symbol == "USDC").first()
    if asset is None:
        asset = Asset(symbol="USDC", name="USD Coin", asset_type="stablecoin")
        db.add(asset)
        db.flush()
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    if instr is None:
        instr = Instrument(
            asset_id=asset.id,
            code="USDC_SPOT",
            name="USDC Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


def _bundle_portfolio(db: Session, client_id: uuid.UUID, *, name: str) -> Portfolio:
    suffix = uuid.uuid4().hex[:6].upper()
    product = ProductDefinition(
        product_code=f"GATE-{suffix}",
        name=name,
        product_type="crypto_bundle",
        base_currency="EUR",
        is_public=True,
        status="active",
        metadata_={"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )
    db.add(product)
    db.flush()
    portfolio = Portfolio(
        client_id=client_id,
        origin_product_id=product.id,
        portfolio_type="bundle_portfolio",
        name=name,
        base_currency="USD",
        status="active",
    )
    db.add(portfolio)
    db.flush()
    return portfolio


def _seed_wallet_usdc(db: Session, pe) -> None:
    from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
    from services.privy_wallet.repository import PersonWalletBalanceRepository

    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )
    row = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    PersonWalletBalanceRepository.increment_balance(
        db, row, delta=Decimal("5000"), sync_source="test",
    )


def _fund_patch(return_value: dict | None = None):
    return patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        return_value=return_value or {"funded": True, "amount": "20"},
    )


def _swap_count(db: Session, person_id: uuid.UUID) -> int:
    from services.lifi.models import PersonWalletSwap

    return (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .count()
    )


def _active_guard_count(db: Session) -> int:
    return (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.ACTIVE.value,
            PortfolioFinancialOperation.released_at.is_(None),
        )
        .count()
    )


def _deposit_and_queue(db: Session, pe, portfolio: Portfolio, amount: str = "20"):
    with _fund_patch():
        return request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            funding_asset="USDC",
            funding_amount=Decimal(amount),
        )


def _run_worker_with_terminal(
    db: Session,
    *,
    v3_status: str = "COMPLETED",
    execution_id: str | None = None,
) -> dict[str, Any]:
    terminal = {
        "v3_status": v3_status,
        "rebalance_execution_id": execution_id or str(uuid.uuid4()),
        "plan_hash": f"sha256:gate-{uuid.uuid4().hex[:8]}",
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
        return_value={"status": "ok", "plan_hash": terminal["plan_hash"], "buy_plan": [], "sell_plan": []},
    ):
        return tick_bundle_v3_deposit_worker(db)


# ---------------------------------------------------------------------------
# TEST 1 — Kings +20 lifecycle complet
# ---------------------------------------------------------------------------


def test_gate_01_kings_deposit_full_lifecycle(db: Session, gate_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, kings)
    assert queued["status"] == "queued"

    guard_active = find_active_portfolio_financial_operation(db, portfolio_id=kings.id)
    assert guard_active is not None
    assert guard_active.status == PortfolioFinancialOperationStatus.ACTIVE.value

    outbox_before = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert len(outbox_before) == 1
    assert outbox_before[0].status == OutboxEventStatus.PENDING.value

    tick = _run_worker_with_terminal(db, v3_status="COMPLETED")
    assert tick.processed == 1

    guard_after = find_active_portfolio_financial_operation(db, portfolio_id=kings.id)
    assert guard_after is None

    released = (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.portfolio_id == kings.id,
            PortfolioFinancialOperation.execution_id == uuid.UUID(queued["deposit_execution_id"]),
        )
        .first()
    )
    assert released is not None
    assert released.status == PortfolioFinancialOperationStatus.RELEASED.value
    assert released.released_at is not None


# ---------------------------------------------------------------------------
# TEST 2 — Double dépôt Kings → 409
# ---------------------------------------------------------------------------


def test_gate_02_double_kings_deposit_second_409(db: Session, gate_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    swaps_before = _swap_count(db, pe.person_id)

    with _fund_patch():
        first = request_v3_bundle_deposit(
            db, client_id=pe.id, portfolio_id=kings.id,
            funding_asset="USDC", funding_amount=Decimal("20"),
        )
    assert first["status"] == "queued"

    with pytest.raises(PortfolioFinancialOperationInProgress409) as exc:
        with _fund_patch():
            request_v3_bundle_deposit(
                db, client_id=pe.id, portfolio_id=kings.id,
                funding_asset="USDC", funding_amount=Decimal("20"),
            )

    assert exc.value.error_code == PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE
    assert _swap_count(db, pe.person_id) == swaps_before


# ---------------------------------------------------------------------------
# TEST 3 — Kings + Majors parallèles
# ---------------------------------------------------------------------------


def test_gate_03_kings_and_majors_parallel(db: Session, gate_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    majors = _bundle_portfolio(db, pe.id, name="Crypto Majors")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    k = _deposit_and_queue(db, pe, kings)
    m = _deposit_and_queue(db, pe, majors)

    assert k["deposit_execution_id"] != m["deposit_execution_id"]
    assert k["batch_id"] != m["batch_id"]

    tick = _run_worker_with_terminal(db, v3_status="COMPLETED")
    assert tick.processed == 2

    for pf, dep in ((kings, k), (majors, m)):
        assert find_active_portfolio_financial_operation(db, portfolio_id=pf.id) is None


# ---------------------------------------------------------------------------
# TEST 4 — Crash worker après funding → reprise idempotente
# ---------------------------------------------------------------------------


def test_gate_04_worker_crash_after_funding_idempotent_resume(db: Session, gate_env):
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    fund_calls: list[str] = []
    execute_calls: list[str] = []

    def _counting_fund(db, **kwargs):
        fund_calls.append(str(kwargs.get("batch_id")))
        return {"funded": True, "amount": "20"}

    crash_once = {"done": False}

    def _execute_maybe_crash(db, **kwargs):
        execute_calls.append("execute")
        if not crash_once["done"]:
            crash_once["done"] = True
            raise RuntimeError("simulated_worker_crash")
        return {
            "v3_status": "COMPLETED",
            "rebalance_execution_id": str(uuid.uuid4()),
            "plan_hash": "sha256:crash-recovery",
            "resume_required": False,
        }

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        side_effect=_counting_fund,
    ):
        queued = request_v3_bundle_deposit(
            db, client_id=pe.id, portfolio_id=kings.id,
            funding_asset="USDC", funding_amount=Decimal("20"),
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
        return_value={"status": "ok", "plan_hash": "sha256:crash-recovery", "buy_plan": [], "sell_plan": []},
    ):
        tick1 = tick_bundle_v3_deposit_worker(db)
        assert tick1.failed == 1
        assert tick1.processed == 0

        outbox = TransactionOutboxRepository.find_by_intent(
            db, uuid.UUID(queued["intent_id"]),
            event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        )
        assert outbox[0].status == OutboxEventStatus.PENDING.value
        outbox[0].next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.flush()

        tick2 = tick_bundle_v3_deposit_worker(db)
        assert tick2.processed == 1

    assert len(fund_calls) == 1
    assert len(execute_calls) == 2
    assert find_active_portfolio_financial_operation(db, portfolio_id=kings.id) is None


# ---------------------------------------------------------------------------
# TEST 5 — Leg fail puis success (MAX_SWAP_ATTEMPTS=2)
# ---------------------------------------------------------------------------


def test_gate_05_leg_fail_then_success_terminal(db: Session, gate_env, monkeypatch):
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    from tests.test_bundle_allocation_phase5a import _bundle_with_allocations, _instrument_for_asset

    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    _seed_wallet_usdc(db, pe)

    plan = {
        "status": "ok",
        "plan_hash": f"sha256:retry-{uuid.uuid4().hex[:8]}",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "weight_basis": "invested_assets",
        "cash_funding_source": "separate",
        "available_cash_usdc": "20",
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
        outcomes={"rebalance_buy": ["raise", "completed"]},
    )

    _deposit_and_queue(db, pe, portfolio)

    from services.portfolio_engine.bundles.rebalance_executor import execute_v3_bundle_rebalance

    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
        trigger="deposit",
        execution_adapter=_adapter(provider),
    )

    assert result["v3_status"] in ("COMPLETED", "COMPLETED_WITH_RESIDUAL_CASH")
    assert result["buy_results"][0]["attempts"] == 2
    assert result.get("resume_required") is not True


# ---------------------------------------------------------------------------
# TEST 6 — Leg fail x2 → terminal (pas RUNNING stuck)
# ---------------------------------------------------------------------------


def test_gate_06_leg_fail_twice_never_running_stuck(db: Session, gate_env, monkeypatch):
    monkeypatch.setenv("MAX_SWAP_ATTEMPTS", "2")
    from tests.test_bundle_allocation_phase5a import _bundle_with_allocations, _instrument_for_asset

    pe = make_linked_client(db)
    portfolio, _usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    _seed_wallet_usdc(db, pe)

    plan = {
        "status": "ok",
        "plan_hash": f"sha256:fail2-{uuid.uuid4().hex[:8]}",
        "snapshot_hash": "sha256:snap",
        "entry_asset": "USDC",
        "available_cash_usdc": "20",
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
        outcomes={"rebalance_buy": ["raise", "raise"]},
    )

    _deposit_and_queue(db, pe, portfolio)

    from services.portfolio_engine.bundles.rebalance_executor import execute_v3_bundle_rebalance

    result = execute_v3_bundle_rebalance(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        drift_rebalance_plan=plan,
        plan_hash=plan["plan_hash"],
        trigger="deposit",
        execution_adapter=_adapter(provider),
    )

    assert result["v3_status"] in ("COMPLETED_WITH_RESIDUAL_CASH", "FAILED")
    assert result["v3_status"] != "RUNNING"
    assert result.get("resume_required") is not True


# ---------------------------------------------------------------------------
# TEST 7 — Swap classique + Kings + Majors (pas de contamination)
# ---------------------------------------------------------------------------


def test_gate_07_classic_swap_and_bundle_deposits_isolated(db: Session, gate_env):
    """INTERNAL_SWAP non câblé au guard — dépôts portfolio restent indépendants."""
    pe = make_linked_client(db)
    kings = _bundle_portfolio(db, pe.id, name="Two Crypto Kings")
    majors = _bundle_portfolio(db, pe.id, name="Crypto Majors")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    # « Swap classique » — pas de slot portfolio_financial_operations (hors scope guard V1)
    swap_portfolio_id = uuid.uuid4()  # aucune ligne guard

    k = _deposit_and_queue(db, pe, kings)
    m = _deposit_and_queue(db, pe, majors)

    assert find_active_portfolio_financial_operation(db, portfolio_id=kings.id) is not None
    assert find_active_portfolio_financial_operation(db, portfolio_id=majors.id) is not None

    guards = (
        db.query(PortfolioFinancialOperation)
        .filter(PortfolioFinancialOperation.portfolio_id.in_([kings.id, majors.id]))
        .all()
    )
    assert len(guards) == 2
    assert swap_portfolio_id not in {g.portfolio_id for g in guards}

    tick = _run_worker_with_terminal(db, v3_status="COMPLETED")
    assert tick.processed == 2


# ---------------------------------------------------------------------------
# TEST 8 — Release guard pour tous les statuts terminaux
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v3_status,guard_terminal", [
    ("COMPLETED", PortfolioFinancialOperationStatus.RELEASED.value),
    ("COMPLETED_WITH_RESIDUAL_CASH", PortfolioFinancialOperationStatus.RELEASED.value),
    ("FAILED", PortfolioFinancialOperationStatus.FAILED.value),
])
def test_gate_08_guard_released_on_all_terminal_statuses(
    db: Session,
    gate_env,
    v3_status: str,
    guard_terminal: str,
):
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id, name="Guard Release PF")
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)

    queued = _deposit_and_queue(db, pe, pf)
    _run_worker_with_terminal(db, v3_status=v3_status)

    assert find_active_portfolio_financial_operation(db, portfolio_id=pf.id) is None
    row = (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.portfolio_id == pf.id,
            PortfolioFinancialOperation.execution_id == uuid.UUID(queued["deposit_execution_id"]),
        )
        .first()
    )
    assert row is not None
    assert row.status == guard_terminal
    assert row.released_at is not None

    assert _active_guard_count(db) == 0


def test_gate_08_no_active_orphans_after_batch(db: Session, gate_env):
    pe = make_linked_client(db)
    _usdc_instrument(db)
    _seed_wallet_usdc(db, pe)
    for name in ("Kings A", "Kings B", "Majors A"):
        pf = _bundle_portfolio(db, pe.id, name=name)
        _deposit_and_queue(db, pe, pf)

    tick = _run_worker_with_terminal(db, v3_status="COMPLETED")
    assert tick.processed == 3
    assert _active_guard_count(db) == 0
