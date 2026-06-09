"""PR-4 — Portfolio Financial Operation Guard."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.financial_operations.enums import (
    PortfolioFinancialOperationStatus,
    PortfolioFinancialOperationType,
)
from services.portfolio_engine.financial_operations.exceptions import (
    PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE,
    PortfolioFinancialOperationInProgress409,
)
from services.portfolio_engine.financial_operations.models import PortfolioFinancialOperation
from services.portfolio_engine.financial_operations.service import (
    acquire_portfolio_financial_operation,
    audit_portfolio_financial_operations,
    expire_stale_portfolio_financial_operations,
    release_portfolio_financial_operation,
)
from services.portfolio_engine.portfolios.models import Portfolio
from tests.conftest import make_linked_client


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
    not _migration_178_ready(),
    reason="Migration 178 requise (portfolio_financial_operations).",
)


def _portfolio(db: Session, client_id: uuid.UUID) -> Portfolio:
    row = Portfolio(
        client_id=client_id,
        portfolio_type="bundle_portfolio",
        name=f"PF-{uuid.uuid4().hex[:6]}",
        base_currency="USD",
        status="active",
    )
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def guard_on(monkeypatch):
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")


@pytest.fixture
def guard_off(monkeypatch):
    monkeypatch.delenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", raising=False)


def test_flag_off_acquire_is_no_op(db: Session, guard_off):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    exec_id = uuid.uuid4()
    result = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=exec_id,
    )
    assert result.skipped is True
    assert result.acquired is False
    assert db.query(PortfolioFinancialOperation).count() == 0


def test_acquire_then_conflict_409(db: Session, guard_on):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    first_exec = uuid.uuid4()
    second_exec = uuid.uuid4()

    first = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=first_exec,
    )
    assert first.acquired is True
    assert first.idempotent is False

    with pytest.raises(PortfolioFinancialOperationInProgress409) as exc_info:
        acquire_portfolio_financial_operation(
            db,
            portfolio_id=pf.id,
            operation_type=PortfolioFinancialOperationType.BUNDLE_REBALANCE_V3,
            execution_id=second_exec,
        )

    exc = exc_info.value
    assert exc.error_code == PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE
    assert exc.existing_execution_id == first_exec
    assert exc.requested_execution_id == second_exec


def test_same_execution_id_is_idempotent(db: Session, guard_on):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    exec_id = uuid.uuid4()

    first = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=exec_id,
    )
    second = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=exec_id,
    )
    assert first.operation is not None
    assert second.idempotent is True
    assert second.operation.id == first.operation.id
    assert db.query(PortfolioFinancialOperation).count() == 1


def test_different_portfolios_allowed(db: Session, guard_on):
    pe = make_linked_client(db)
    pf_a = _portfolio(db, pe.id)
    pf_b = _portfolio(db, pe.id)

    acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf_a.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=uuid.uuid4(),
    )
    second = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf_b.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_REBALANCE_V3,
        execution_id=uuid.uuid4(),
    )
    assert second.acquired is True


def test_release_frees_slot(db: Session, guard_on):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    exec_id = uuid.uuid4()

    acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=exec_id,
    )
    released = release_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        execution_id=exec_id,
    )
    assert released is True

    again = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=uuid.uuid4(),
    )
    assert again.acquired is True
    assert again.idempotent is False


def test_expire_stale_operations(db: Session, guard_on):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    exec_id = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(minutes=5)

    row = PortfolioFinancialOperation(
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST.value,
        execution_id=exec_id,
        status=PortfolioFinancialOperationStatus.ACTIVE.value,
        started_at=past,
        expires_at=past,
    )
    db.add(row)
    db.flush()

    expired_count = expire_stale_portfolio_financial_operations(db, portfolio_id=pf.id)
    assert expired_count == 1
    db.refresh(row)
    assert row.status == PortfolioFinancialOperationStatus.EXPIRED.value

    acquired = acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=uuid.uuid4(),
    )
    assert acquired.acquired is True


def test_audit_returns_active_operation(db: Session, guard_on):
    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)
    exec_id = uuid.uuid4()
    acquire_portfolio_financial_operation(
        db,
        portfolio_id=pf.id,
        operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST,
        execution_id=exec_id,
    )

    audit = audit_portfolio_financial_operations(db, portfolio_id=pf.id)
    assert audit["guard_enabled"] is True
    assert audit["active_operation"] is not None
    assert audit["active_operation"]["execution_id"] == str(exec_id)
    assert audit["active_operation"]["operation_type"] == "BUNDLE_INVEST"


def test_orchestrator_double_invest_blocked_while_pending(
    db: Session,
    guard_on,
    monkeypatch,
):
    """Critère succès PR-4 — Kings +20 puis +20 immédiat → conflit guard portefeuille."""
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    pe = make_linked_client(db)
    pf = _portfolio(db, pe.id)

    def _fake_invest_via_lifi(self, db, **kwargs):
        from services.portfolio_engine.financial_operations.wiring import (
            acquire_bundle_invest_portfolio_operation,
        )

        batch_id = str(uuid.uuid4())
        acquire_bundle_invest_portfolio_operation(
            db,
            portfolio_id=kwargs["portfolio_id"],
            batch_id=batch_id,
        )
        return {
            "status": "pending_signature",
            "batch_id": batch_id,
            "portfolio_id": str(kwargs["portfolio_id"]),
        }

    monkeypatch.setattr(BundleOrchestrator, "_invest_via_lifi", _fake_invest_via_lifi)
    monkeypatch.setattr(
        BundleOrchestrator,
        "_load_and_validate_portfolio",
        lambda self, db, portfolio_id, client_id: pf,
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_load_product",
        lambda self, db, portfolio: type("P", (), {"metadata_": {"entry_asset_default": "USDC"}})(),
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_entry_config",
        lambda self, product: {"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_load_target_allocations",
        lambda self, db, portfolio_id: [object()],
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_or_create_instrument",
        lambda self, db, entry_asset: type("I", (), {"id": uuid.uuid4()})(),
    )

    orchestrator = BundleOrchestrator()
    monkeypatch.setattr(
        orchestrator,
        "_execution",
        type("E", (), {"provider_name": "lifi_base"})(),
    )
    first = orchestrator.invest_into_bundle(
        db,
        client_id=pe.id,
        portfolio_id=pf.id,
        funding_asset="USDC",
        funding_amount=20,
    )
    assert first["status"] == "pending_signature"

    with pytest.raises(PortfolioFinancialOperationInProgress409) as exc_info:
        orchestrator.invest_into_bundle(
            db,
            client_id=pe.id,
            portfolio_id=pf.id,
            funding_asset="USDC",
            funding_amount=20,
        )

    assert exc_info.value.error_code == PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE


def test_in_progress_exception_response_shape():
    exc = PortfolioFinancialOperationInProgress409(
        portfolio_id=uuid.uuid4(),
        existing_operation_type="BUNDLE_INVEST",
        existing_execution_id=uuid.uuid4(),
        requested_operation_type="BUNDLE_INVEST",
        requested_execution_id=uuid.uuid4(),
    )
    body = exc.to_response()
    assert body["error_code"] == PORTFOLIO_FINANCIAL_OPERATION_IN_PROGRESS_CODE
    assert body["status"] == "portfolio_financial_operation_in_progress"
