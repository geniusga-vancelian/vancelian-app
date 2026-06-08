"""Legacy Bundle — re-quote buy-only après legs invest EXPIRED."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundles.bundle_invest_lock import (
    BUNDLE_BATCH_RECOVERY_KEY,
    get_invest_lock,
)
from services.portfolio_engine.bundles.orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
    POSITION_TYPE_SPOT,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from tests.test_bundle_allocation_phase5a import _bundle_with_allocations, _instrument_for_asset
from tests.test_bundle_expired_invest_legs import (
    _pe_cb_counts,
    _seed_swap,
    _stub_resume_deps,
)
from conftest import make_linked_client


def _credit_cash_leg(db: Session, portfolio_id, instrument_id, amount: str):
    from tests.test_bundle_lifi_funding import _instrument_usdc

    usdc = _instrument_usdc(db)
    assert str(instrument_id) == str(usdc.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio_id, instrument_id, Decimal(amount), Decimal(amount),
    )


def _spot_qty(db: Session, portfolio_id, instrument_id) -> Decimal:
    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == instrument_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
            PositionAtom.status == "open",
        )
        .first()
    )
    return Decimal(str(atom.quantity or 0)) if atom else Decimal("0")


def test_requote_expired_batch_creates_new_swaps(db: Session, monkeypatch):
    """Shape 470c964f — deux legs EXPIRED → re-quote crée nouveaux swaps pending."""
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")
    pe = make_linked_client(db)
    old_batch_id = "470c964f-0000-4000-8000-000000000001"
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": old_batch_id,
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.flush()
    _credit_cash_leg(db, portfolio.id, usdc.id, "30.90")
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBBTC",
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBETH",
    )
    db.commit()
    pe_before, cb_before = _pe_cb_counts(db)
    cash_before = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc.id,
    )

    created_assets: list[str] = []
    new_swap_ids: list[str] = []

    def _fake_run_leg(self, db, *, target_asset, batch_id, **kwargs):
        created_assets.append(target_asset)
        swap_id = str(uuid.uuid4())
        new_swap_ids.append(swap_id)
        return {
            "status": "pending",
            "record": {
                "asset": target_asset,
                "status": "pending",
                "swap_id": swap_id,
                "leg_id": kwargs.get("ext_ref"),
            },
        }

    _stub_resume_deps(monkeypatch)
    monkeypatch.setattr(BundleOrchestrator, "_run_allocation_leg", _fake_run_leg)

    result = BundleOrchestrator().requote_expired_invest_legs(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    db.commit()
    db.refresh(p)

    assert result["requoted"] is True
    assert result["recovery_from_batch_id"] == old_batch_id
    assert result["batch_id"] != old_batch_id
    assert result["legs_pending"] == 2
    assert set(created_assets) == {"CBBTC", "CBETH"}

    cash_after = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc.id,
    )
    assert cash_after == cash_before

    lock = get_invest_lock(p.metadata_)
    assert lock is not None
    assert lock["batch_id"] == result["batch_id"]
    assert lock["recovery_from_batch_id"] == old_batch_id

    recovery = (p.metadata_ or {}).get(BUNDLE_BATCH_RECOVERY_KEY, {})
    assert recovery[old_batch_id]["status"] == "requoted"
    assert recovery[old_batch_id]["recovery_batch_id"] == result["batch_id"]

    pe_after, cb_after = _pe_cb_counts(db)
    assert pe_after == pe_before
    assert cb_after == cb_before


def test_requote_mixed_confirmed_skips_confirmed_asset(db: Session, monkeypatch):
    """BTC confirmé inchangé — re-quote ne crée qu'un swap CBETH."""
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")
    pe = make_linked_client(db)
    old_batch_id = str(uuid.uuid4())
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": old_batch_id,
            "status": "signature_requested",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.flush()
    btc = _instrument_for_asset(db, "BTC")
    eth = _instrument_for_asset(db, "ETH")
    _credit_cash_leg(db, portfolio.id, usdc.id, "15")
    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, btc.id, Decimal("0.001"), Decimal("50"),
    )
    btc_before = _spot_qty(db, portfolio.id, btc.id)
    eth_before = _spot_qty(db, portfolio.id, eth.id)

    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.CONFIRMED.value, to_asset="CBBTC",
    )
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.EXPIRED.value, to_asset="CBETH",
    )
    db.commit()

    created: list[str] = []

    def _fake_run_leg(self, db, *, target_asset, **kwargs):
        created.append(target_asset)
        return {
            "status": "pending",
            "record": {"asset": target_asset, "status": "pending", "swap_id": str(uuid.uuid4())},
        }

    _stub_resume_deps(monkeypatch)
    monkeypatch.setattr(BundleOrchestrator, "_run_allocation_leg", _fake_run_leg)

    result = BundleOrchestrator().requote_expired_invest_legs(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )

    assert result["legs_pending"] == 1
    assert created == ["CBETH"]
    assert _spot_qty(db, portfolio.id, btc.id) == btc_before
    assert _spot_qty(db, portfolio.id, eth.id) == eth_before


def test_requote_no_pending_required(db: Session):
    pe = make_linked_client(db)
    old_batch_id = str(uuid.uuid4())
    portfolio, usdc = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1")})
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": old_batch_id,
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.flush()
    _credit_cash_leg(db, portfolio.id, usdc.id, "10")
    _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
    )
    db.commit()

    with pytest.raises(BundleOrchestratorError, match="pending_invest_legs_block_requote"):
        BundleOrchestrator().requote_expired_invest_legs(
            db, client_id=pe.id, portfolio_id=portfolio.id,
        )


def test_requote_marks_expired_swap_audit(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")
    pe = make_linked_client(db)
    old_batch_id = str(uuid.uuid4())
    portfolio, usdc = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1")})
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": old_batch_id,
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.flush()
    _credit_cash_leg(db, portfolio.id, usdc.id, "10")
    expired = _seed_swap(
        db, pe, portfolio_id=str(portfolio.id), batch_id=old_batch_id,
        status=SwapSessionStatus.EXPIRED.value,
    )
    db.commit()

    def _fake_run_leg(self, db, *, target_asset, **kwargs):
        return {
            "status": "pending",
            "record": {"asset": target_asset, "status": "pending", "swap_id": str(uuid.uuid4())},
        }

    _stub_resume_deps(monkeypatch)
    monkeypatch.setattr(BundleOrchestrator, "_run_allocation_leg", _fake_run_leg)

    result = BundleOrchestrator().requote_expired_invest_legs(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    db.refresh(expired)
    events = [e.get("event") for e in (expired.audit_log or []) if isinstance(e, dict)]
    assert "bundle_expired_requoted" in events
    assert result["recovery_status"] == "recovery_started"
