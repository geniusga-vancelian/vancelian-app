"""Legacy Bundle resume — expired invest legs explicit error."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.orchestrator import (
    BundleExpiredInvestLegsError,
    BundleOrchestrator,
    BundleOrchestratorError,
)
from services.portfolio_engine.portfolios.models import Portfolio
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
    status: str,
    to_asset: str = "CBBTC",
) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
        from_asset="USDC",
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=portfolio_id, batch_id=batch_id),
    )
    db.add(swap)
    db.flush()
    return swap


def _portfolio_with_lock(db: Session, pe, *, batch_id: str) -> Portfolio:
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.commit()
    return portfolio


def _pe_cb_counts(db: Session) -> tuple[int, int]:
    pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    return int(pe or 0), int(cb or 0)


def _stub_resume_deps(monkeypatch):
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


def test_resume_expired_swaps_returns_expired_invest_legs(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBBTC",
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBETH",
    )
    db.commit()
    pe_before, cb_before = _pe_cb_counts(db)

    with pytest.raises(BundleExpiredInvestLegsError) as exc_info:
        BundleOrchestrator().resume_lifi_invest_batch(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
        )
    db.rollback()

    resp = exc_info.value.to_response()
    assert resp["error_code"] == "expired_invest_legs"
    assert resp["action"] == "re_quote_required"
    assert resp["expired_count"] == 2
    assert set(resp["expired_assets"]) == {"CBBTC", "CBETH"}
    pe_after, cb_after = _pe_cb_counts(db)
    assert pe_after == pe_before
    assert cb_after == cb_before


def test_resume_awaiting_signature_normal(db: Session, monkeypatch):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    db.commit()
    _stub_resume_deps(monkeypatch)

    result = BundleOrchestrator().resume_lifi_invest_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    assert result["legs_pending"] == 1


def test_resume_submitted_normal(db: Session, monkeypatch):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.SUBMITTED.value,
    )
    db.commit()
    _stub_resume_deps(monkeypatch)

    result = BundleOrchestrator().resume_lifi_invest_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    assert result["legs_pending"] == 1


def test_resume_no_swaps_returns_no_pending_invest_legs(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)

    with pytest.raises(BundleOrchestratorError, match="no_pending_invest_legs"):
        BundleOrchestrator().resume_lifi_invest_batch(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
        )


def test_resume_mixed_confirmed_and_expired_returns_expired_invest_legs(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.CONFIRMED.value, to_asset="CBBTC",
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBETH",
    )
    db.commit()

    with pytest.raises(BundleExpiredInvestLegsError) as exc_info:
        BundleOrchestrator().resume_lifi_invest_batch(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
        )
    assert exc_info.value.to_response()["expired_count"] == 1
    assert exc_info.value.to_response()["expired_assets"] == ["CBETH"]


def test_resume_expired_does_not_auto_requote(db: Session, monkeypatch):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_lock(db, pe, batch_id=batch_id)
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=batch_id,
        status=SwapSessionStatus.EXPIRED.value,
    )
    db.commit()

    called = {"prepare": 0}
    _stub_resume_deps(monkeypatch)
    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService

    def _track_prepare(self, db, *, person_id, swap_id):
        called["prepare"] += 1
        raise AssertionError("prepare_signing should not run for expired legs")

    monkeypatch.setattr(BundleLifiLegService, "prepare_signing", _track_prepare)

    with pytest.raises(BundleExpiredInvestLegsError):
        BundleOrchestrator().resume_lifi_invest_batch(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
        )
    assert called["prepare"] == 0
