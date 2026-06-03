"""Tests read model réconciliation bundle — R4.5-E.2-A (lecture seule)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.bundle_invest_lock import acquire_invest_lock
from services.portfolio_engine.bundles.bundle_reconciliation_read_model import (
    ACTION_COMPLETE_WITH_CASH_RESIDUAL,
    ACTION_RETRY_MISSING_LEG,
    STATUS_RECONCILIATION_REQUIRED,
    build_bundle_reconciliation_state,
    is_lock_zombie,
    resolve_reconciliation_status,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.enums import IntentStatus
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc
from tests.test_bundle_self_trading_isolation import _bundle_swap_audit


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def test_zombie_lock_when_ttl_exceeded_and_swap_stuck():
    now = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
    old = now - timedelta(minutes=200)
    lock = {
        "batch_id": str(uuid.uuid4()),
        "status": "signature_requested",
        "created_at": _utc_iso(old),
        "updated_at": _utc_iso(old),
    }
    confirmed = PersonWalletSwap(
        person_id=uuid.uuid4(),
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2.8"),
        estimated_receive=Decimal("0.00004"),
        created_at=old,
        updated_at=old,
    )
    pending = PersonWalletSwap(
        person_id=uuid.uuid4(),
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1.2"),
        estimated_receive=Decimal("0.001"),
        created_at=old,
        updated_at=old,
    )
    with patch(
        "services.portfolio_engine.bundles.bundle_reconciliation_read_model.invest_lock_ttl_minutes",
        return_value=120,
    ):
        assert is_lock_zombie(
            lock,
            intent_status=IntentStatus.PARTIAL.value,
            allocation_swaps=[confirmed, pending],
            now=now,
        ) is True


def test_not_zombie_when_within_ttl():
    now = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
    recent = now - timedelta(minutes=30)
    lock = {
        "status": "signature_requested",
        "created_at": _utc_iso(recent),
        "updated_at": _utc_iso(recent),
    }
    swap = PersonWalletSwap(
        person_id=uuid.uuid4(),
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        estimated_receive=Decimal("0.001"),
        created_at=recent,
        updated_at=recent,
    )
    with patch(
        "services.portfolio_engine.bundles.bundle_reconciliation_read_model.invest_lock_ttl_minutes",
        return_value=120,
    ):
        assert is_lock_zombie(
            lock,
            intent_status=IntentStatus.PARTIAL.value,
            allocation_swaps=[swap],
            now=now,
        ) is False


def test_partial_confirmed_and_pending_maps_reconciliation_required():
    confirmed = PersonWalletSwap(
        person_id=uuid.uuid4(),
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2.8"),
        estimated_receive=Decimal("0.00004"),
    )
    pending = PersonWalletSwap(
        person_id=uuid.uuid4(),
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1.2"),
        estimated_receive=Decimal("0.001"),
    )
    status = resolve_reconciliation_status(
        intent_status=IntentStatus.PARTIAL.value,
        allocation_swaps=[confirmed, pending],
        cash_residual_usdc=4.2,
        lock=None,
        lock_zombie=False,
    )
    assert status == STATUS_RECONCILIATION_REQUIRED


def test_build_state_partial_batch(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    usdc = _instrument_usdc(db)
    now = datetime.now(timezone.utc)
    stale = now - timedelta(minutes=200)

    acquire_invest_lock(
        db,
        p,
        client_id=pe.id,
        batch_id=batch_id,
        entry_instrument_id=str(usdc.id),
        status="signature_requested",
    )
    lock_meta = dict(p.metadata_ or {}).get("bundle_invest_lock") or {}
    lock_meta["created_at"] = _utc_iso(stale)
    lock_meta["updated_at"] = _utc_iso(stale)
    meta = dict(p.metadata_ or {})
    meta["bundle_invest_lock"] = lock_meta
    p.metadata_ = meta
    db.add(p)

    confirmed = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2.8"),
        estimated_receive=Decimal("0.00004"),
        tx_hash="0xabc",
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
        created_at=stale,
        updated_at=stale,
    )
    pending = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1.2"),
        estimated_receive=Decimal("0.001"),
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
        created_at=stale,
        updated_at=stale,
    )
    db.add(confirmed)
    db.add(pending)
    db.commit()
    db.refresh(p)

    with patch(
        "services.portfolio_engine.bundles.bundle_reconciliation_read_model.invest_lock_ttl_minutes",
        return_value=120,
    ):
        state = build_bundle_reconciliation_state(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            now=now,
        )

    assert state["read_only"] is True
    assert state["batch_id"] == batch_id
    assert state["status"] == STATUS_RECONCILIATION_REQUIRED
    assert len(state["confirmed_allocations"]) == 1
    assert state["confirmed_allocations"][0]["asset"] == "CBBTC"
    assert len(state["pending_allocations"]) == 1
    assert state["pending_allocations"][0]["status"] == "awaiting_signature"
    assert ACTION_RETRY_MISSING_LEG in state["available_actions"]
    assert ACTION_COMPLETE_WITH_CASH_RESIDUAL in state["available_actions"]
    if state["lock"]["present"] and (state["lock"]["age_minutes"] or 0) >= 120:
        assert state["lock"]["zombie"] is True
