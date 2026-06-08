"""P0 — bundle_invest_lock orphaning fix (read-only GET + reconcile guard + resume fallback)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.bundle_invest_lock import (
    AUDIT_ACTION_LOCK_REACQUIRED,
    AUDIT_ACTION_RECONCILE_SKIPPED,
    acquire_invest_lock,
    get_invest_lock,
    peek_bundle_invest_lock_state,
    reconcile_idle_invest_lock,
    reconcile_or_expire_idle_invest_lock,
    update_invest_lock_status,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator, BundleOrchestratorError
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.bundle_intent_sync import ensure_bundle_parent_intent
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str, action: str = "allocation"):
    return [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": batch_id,
            "bundle_action": action,
            "leg_action": action,
        }
    ]


def _seed_swap(
    db: Session,
    pe,
    *,
    portfolio_id: str,
    batch_id: str,
    status: str = SwapSessionStatus.AWAITING_SIGNATURE.value,
) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=portfolio_id, batch_id=batch_id),
    )
    db.add(swap)
    db.flush()
    return swap


def _portfolio_with_lock(
    db: Session,
    pe,
    *,
    batch_id: str,
    status: str = "pending_signature",
) -> tuple[Portfolio, Portfolio]:
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.commit()
    return portfolio, p


def test_active_lock_peek_is_read_only(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio, p = _portfolio_with_lock(db, pe, batch_id=batch_id)
    meta_before = dict(p.metadata_ or {})

    state = peek_bundle_invest_lock_state(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )

    db.refresh(p)
    assert (p.metadata_ or {}) == meta_before
    assert state["read_only"] is True
    assert state["status"] == "active"
    assert state["lock"]["batch_id"] == batch_id
    assert db.query(AuditEvent).filter(
        AuditEvent.action == AUDIT_ACTION_RECONCILE_SKIPPED,
    ).count() == 0


def test_reconcile_idle_preserves_lock_with_awaiting_signature_swaps(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio, p = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    db.commit()

    assert not reconcile_idle_invest_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=p,
    )
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is not None


def test_reconcile_idle_preserves_lock_with_submitted_swaps(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio, p = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.SUBMITTED.value,
    )
    db.commit()

    assert not reconcile_idle_invest_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=p,
    )
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is not None


def test_reconcile_checks_all_batches_not_only_lock_batch(db: Session):
    pe = make_linked_client(db)
    lock_batch = str(uuid.uuid4())
    other_batch = str(uuid.uuid4())
    portfolio, p = _portfolio_with_lock(db, pe, batch_id=lock_batch)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=other_batch,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    db.commit()

    assert not reconcile_idle_invest_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=p,
    )
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is not None
    assert db.query(AuditEvent).filter(
        AuditEvent.action == AUDIT_ACTION_RECONCILE_SKIPPED,
    ).count() >= 1


def test_update_invest_lock_status_reacquires_when_cleared_mid_batch(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    p.metadata_ = {}
    db.add(p)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
    )
    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
        extra_metadata={"funding_amount": "20", "funding_asset": "USDC"},
    )
    db.commit()

    lock = update_invest_lock_status(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        status="pending_signature",
    )
    db.commit()
    db.refresh(p)

    assert lock is not None
    assert lock["batch_id"] == batch_id
    assert get_invest_lock(p.metadata_) is not None
    assert db.query(AuditEvent).filter(
        AuditEvent.action == AUDIT_ACTION_LOCK_REACQUIRED,
    ).count() >= 1


def test_resume_lifi_invest_batch_without_lock_metadata_single_active_batch(db: Session, monkeypatch):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    p.metadata_ = {}
    db.add(p)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
    )
    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
    )
    db.commit()

    monkeypatch.setattr(
        BundleOrchestrator,
        "_load_product",
        lambda self, db, portfolio: MagicMock(
            metadata_={"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
        ),
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_entry_config",
        lambda self, product: {"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_or_create_instrument",
        lambda self, db, entry_asset: __import__(
            "tests.test_bundle_lifi_funding", fromlist=["_instrument_usdc"],
        )._instrument_usdc(db),
    )

    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService

    class _SigningStub:
        def model_dump(self):
            return {"stub": True}

    monkeypatch.setattr(
        BundleLifiLegService,
        "prepare_signing",
        lambda self, db, *, person_id, swap_id: _SigningStub(),
    )

    result = BundleOrchestrator().resume_lifi_invest_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    db.commit()
    db.refresh(p)

    assert result["recovered_from_pending_batch"] is True
    assert result["batch_id"] == batch_id
    assert result["legs_pending"] >= 1
    assert get_invest_lock(p.metadata_) is not None


def test_resume_lifi_invest_batch_without_lock_metadata_multiple_active_batches_refuses(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    p.metadata_ = {}
    db.add(p)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=str(uuid.uuid4()),
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=str(uuid.uuid4()),
    )
    db.commit()

    with pytest.raises(BundleOrchestratorError, match="multiple_active_bundle_batches"):
        BundleOrchestrator().resume_lifi_invest_batch(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
        )


def test_partial_batch_hidden_regression_470c964f_shape(db: Session, monkeypatch):
    """Funding ok, parent awaiting_signature, swaps pending, lock null → peek + resume retrouvent le batch."""
    pe = make_linked_client(db)
    batch_id = "470c964f-e166-4b93-97c7-b184510e2523"
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    p.metadata_ = {}
    db.add(p)

    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
        extra_metadata={"funding_amount": "20", "funding_asset": "USDC"},
    )
    db.commit()

    peek = peek_bundle_invest_lock_state(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    assert peek["status"] == "active"
    assert peek["recovered_from_pending_batch"] is True
    assert peek["lock"]["batch_id"] == batch_id
    assert get_invest_lock(p.metadata_) is None

    reconciled = reconcile_or_expire_idle_invest_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=p,
    )
    assert reconciled is True
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is None

    monkeypatch.setattr(
        BundleOrchestrator,
        "_load_product",
        lambda self, db, portfolio: MagicMock(
            metadata_={"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
        ),
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_entry_config",
        lambda self, product: {"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )
    monkeypatch.setattr(
        BundleOrchestrator,
        "_resolve_or_create_instrument",
        lambda self, db, entry_asset: __import__(
            "tests.test_bundle_lifi_funding", fromlist=["_instrument_usdc"],
        )._instrument_usdc(db),
    )
    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService

    class _SigningStub:
        def model_dump(self):
            return {"stub": True}

    monkeypatch.setattr(
        BundleLifiLegService,
        "prepare_signing",
        lambda self, db, *, person_id, swap_id: _SigningStub(),
    )

    resume = BundleOrchestrator().resume_lifi_invest_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    db.commit()
    db.refresh(p)

    assert resume["recovered_from_pending_batch"] is True
    assert resume["legs_pending"] == 2
    assert get_invest_lock(p.metadata_) is not None
