"""Tests — Bundle V3 Deposit Flow (fund + queue + rebalance V3)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.bundle_v3_deposit_flow import (
    V3DepositFlowError,
    request_v3_bundle_deposit,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.worker import (
    tick_bundle_v3_deposit_worker,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client


def _migration_173_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_outbox'"
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


def _migration_178_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'portfolio_financial_operations'"
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_migration_173_ready() and _migration_178_ready()),
    reason="Migrations 173+178 requises.",
)


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


def _bundle_portfolio(db: Session, client_id: uuid.UUID) -> Portfolio:
    suffix = uuid.uuid4().hex[:6].upper()
    product = ProductDefinition(
        product_code=f"V3DEP-{suffix}",
        name=f"V3 Deposit {suffix}",
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
        name="V3 Deposit PF",
        base_currency="USD",
        status="active",
    )
    db.add(portfolio)
    db.flush()
    return portfolio


@pytest.fixture
def v3_deposit_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_FLOW_ENABLED", "true")
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")


@pytest.fixture
def v3_worker_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", "true")


def test_request_disabled_when_flag_off(db: Session, monkeypatch):
    monkeypatch.delenv("BUNDLE_V3_DEPOSIT_FLOW_ENABLED", raising=False)
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    with pytest.raises(V3DepositFlowError) as exc_info:
        request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )
    assert exc_info.value.code == "v3_deposit_flow_disabled"


def test_request_propagates_insufficient_self_trading_code(db: Session, v3_deposit_on):
    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    usdc = _usdc_instrument(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("5"), Decimal("5"))
    db.commit()

    with pytest.raises(V3DepositFlowError) as exc_info:
        request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )
    assert exc_info.value.code == "bundle.funding.insufficient_self_trading"


def test_request_funds_and_enqueues_outbox(db: Session, v3_deposit_on, monkeypatch):
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    _usdc_instrument(db)

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
        db, row, delta=Decimal("1000"), sync_source="test",
    )

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        return_value={"funded": True, "amount": "20"},
    ):
        result = request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )

    assert result["status"] == "queued"
    assert result["worker_immediate_kick"] == "skipped"
    assert result["flow"] == "bundle_v3_deposit"
    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(result["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert len(outbox) == 1


def test_worker_processes_outbox_terminal(db: Session, v3_deposit_on, monkeypatch):
    """Worker cron seul — kick immédiat désactivé."""
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_IMMEDIATE_KICK_ENABLED", "false")
    monkeypatch.setenv("BUNDLE_V3_DEPOSIT_WORKER_ENABLED", "true")
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    _usdc_instrument(db)

    terminal_result = {
        "v3_status": "COMPLETED",
        "rebalance_execution_id": str(uuid.uuid4()),
        "plan_hash": "sha256:test",
    }

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        return_value={"funded": True},
    ):
        queued = request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )

    assert queued["worker_immediate_kick"] == "skipped"

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        return_value=terminal_result,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(pf.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "sha256:test", "buy_plan": [], "sell_plan": []},
    ):
        tick = tick_bundle_v3_deposit_worker(db)

    assert tick.processed == 1
    assert tick.failed == 0
    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(queued["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox[0].status == "processed"


def test_immediate_kick_completes_without_cron(db: Session, v3_deposit_on, v3_worker_on, monkeypatch):
    """Kick post-dépôt — terminal sans tick ECS."""
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    _usdc_instrument(db)

    terminal_result = {
        "v3_status": "COMPLETED",
        "rebalance_execution_id": str(uuid.uuid4()),
        "plan_hash": "sha256:immediate",
        "resume_required": False,
    }

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        return_value={"funded": True},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        return_value=terminal_result,
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(pf.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "sha256:immediate", "buy_plan": [], "sell_plan": []},
    ):
        result = request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )

    assert result["status"] == "completed"
    assert result["worker_immediate_kick"] == "success"
    assert result["v3_status"] == "COMPLETED"

    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(result["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox[0].status == "processed"

    tick = tick_bundle_v3_deposit_worker(db)
    assert tick.polled == 0
    assert tick.processed == 0


def test_immediate_kick_failure_leaves_pending_for_cron(db: Session, v3_deposit_on, v3_worker_on):
    """Échec kick immédiat — outbox PENDING, cron peut reprendre."""
    pe = make_linked_client(db)
    pf = _bundle_portfolio(db, pe.id)
    _usdc_instrument(db)

    terminal_result = {
        "v3_status": "COMPLETED",
        "rebalance_execution_id": str(uuid.uuid4()),
        "plan_hash": "sha256:retry-cron",
    }

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.fund_bundle_cash_leg_from_self_trading",
        return_value={"funded": True},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        side_effect=RuntimeError("simulated_kick_fail"),
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.compute_bundle_drift_snapshot",
        return_value={"portfolio_id": str(pf.id)},
    ), patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "sha256:retry-cron", "buy_plan": [], "sell_plan": []},
    ):
        result = request_v3_bundle_deposit(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=Decimal("20"),
        )

    assert result["status"] == "queued"
    assert result["worker_immediate_kick"] == "failed"

    outbox = TransactionOutboxRepository.find_by_intent(
        db,
        uuid.UUID(result["intent_id"]),
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
    )
    assert outbox[0].status == "pending"

    with patch(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.execute_v3_bundle_rebalance",
        return_value=terminal_result,
    ):
        tick = tick_bundle_v3_deposit_worker(db)

    assert tick.processed == 1
    assert outbox[0].status == "processed"
