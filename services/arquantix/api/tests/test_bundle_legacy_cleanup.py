"""Tests cleanup legacy bundle zombie — R4.5-E.2-C."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import (
    acquire_invest_lock,
    get_invest_lock,
)
from services.portfolio_engine.bundles.bundle_legacy_cleanup import (
    AUDIT_ACTION_OPS_COMPLETED_PARTIAL,
    BundleLegacyCleanupRejected,
    TERMINAL_OUTCOME_COMPLETED_PARTIAL,
    audit_legacy_bundle_cleanup,
    complete_legacy_bundle_with_cash_residual,
    plan_legacy_cleanup_writes,
    snapshot_pe_bundle_positions,
    validate_legacy_cleanup_preconditions,
)
from services.portfolio_engine.bundles.bundle_reconciliation_read_model import (
    STATUS_RECONCILIATION_REQUIRED,
    build_bundle_reconciliation_state,
    is_lock_zombie,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.bundle_intent_sync import (
    ensure_bundle_parent_intent,
    register_bundle_leg,
)
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.repository import TransactionIntentRepository
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc
from tests.test_bundle_self_trading_isolation import _bundle_swap_audit


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@contextmanager
def _legacy_cleanup_test_patches():
    with (
        patch(
            "services.portfolio_engine.bundles.bundle_reconciliation_read_model.invest_lock_ttl_minutes",
            return_value=120,
        ),
        patch(
            "services.portfolio_engine.bundles.bundle_reconciliation_read_model.reconciliation_stale_progress_minutes",
            return_value=30,
        ),
        patch(
            "services.portfolio_engine.bundles.bundle_legacy_cleanup.reconcile_bundle_ledger_shadow",
            return_value={"verdict": "MATCH", "read_only": True},
        ),
    ):
        yield


def _legacy_zombie_fixture(db: Session):
    """Batch partial + lock zombie + CBBTC confirmé + CBETH awaiting_signature."""
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    usdc = _instrument_usdc(db)
    now = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
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

    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
    )
    intent = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
    )
    assert intent is not None
    intent.status = IntentStatus.PARTIAL.value
    db.add(intent)

    leg_btc = f"bundle-alloc-{batch_id}-CBBTC"
    leg_eth = f"bundle-alloc-{batch_id}-CBETH"
    swap_btc = uuid.uuid4()
    swap_eth = uuid.uuid4()
    register_bundle_leg(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
        leg_id=leg_btc,
        swap_id=str(swap_btc),
        asset="CBBTC",
    )
    register_bundle_leg(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
        leg_id=leg_eth,
        swap_id=str(swap_eth),
        asset="CBETH",
    )

    confirmed = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2.8"),
        estimated_receive=Decimal("0.00004"),
        tx_hash="0xconfirmedbtc",
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
    db.flush()
    confirmed.updated_at = stale
    confirmed.created_at = stale
    pending.updated_at = stale
    pending.created_at = stale
    db.add(confirmed)
    db.add(pending)
    db.commit()
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    intent = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
    )
    if intent is not None:
        intent.status = IntentStatus.PARTIAL.value
        db.add(intent)
    meta = dict(p.metadata_ or {})
    lock_meta = dict(meta.get("bundle_invest_lock") or {})
    lock_meta["created_at"] = _utc_iso(stale)
    lock_meta["updated_at"] = _utc_iso(stale)
    lock_meta["status"] = "signature_requested"
    meta["bundle_invest_lock"] = lock_meta
    p.metadata_ = meta
    db.add(p)
    db.commit()
    db.refresh(p)

    return pe, portfolio, batch_id, swap_eth, now


def test_dry_run_does_not_mutate_db(db: Session):
    pe, portfolio, batch_id, _swap_eth, now = _legacy_zombie_fixture(db)
    pe_before = snapshot_pe_bundle_positions(db, portfolio_id=portfolio.id)
    lock_before = get_invest_lock(
        db.query(Portfolio).filter(Portfolio.id == portfolio.id).first().metadata_
    )

    with _legacy_cleanup_test_patches():
        result = complete_legacy_bundle_with_cash_residual(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            idempotency_key=f"dry-{batch_id}",
            actor_id="test-ops",
            dry_run=True,
            now=now,
        )

    assert result["dry_run"] is True
    assert result["mutations_applied"] is False
    db.commit()
    db.refresh(db.query(Portfolio).filter(Portfolio.id == portfolio.id).first())
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    assert get_invest_lock(p.metadata_) == lock_before
    assert snapshot_pe_bundle_positions(db, portfolio_id=portfolio.id) == pe_before


def test_apply_idempotent_and_lock_cleared(db: Session):
    pe, portfolio, batch_id, swap_eth, now = _legacy_zombie_fixture(db)
    key = f"apply-{batch_id}"

    with _legacy_cleanup_test_patches():
        first = complete_legacy_bundle_with_cash_residual(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            idempotency_key=key,
            actor_id="test-ops",
            dry_run=False,
            now=now,
        )
        db.commit()
        second = complete_legacy_bundle_with_cash_residual(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            idempotency_key=key,
            actor_id="test-ops",
            dry_run=False,
            now=now,
        )

    assert first["mutations_applied"] is True
    assert second["already_applied"] is True
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    assert get_invest_lock(p.metadata_) is None

    pending_swap = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == pe.person_id,
            PersonWalletSwap.to_asset == "CBETH",
        )
        .order_by(PersonWalletSwap.created_at.desc())
        .first()
    )
    assert pending_swap is not None
    assert pending_swap.status == SwapSessionStatus.EXPIRED.value

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=pe.person_id,
        bundle_id=str(portfolio.id),
        batch_id=batch_id,
    )
    assert intent is not None
    meta = intent.metadata_json or {}
    assert meta.get("terminal_outcome") == TERMINAL_OUTCOME_COMPLETED_PARTIAL
    assert meta.get("legacy_cleanup") is True
    assert float(meta.get("cash_residual_usdc") or 0) >= 0

    audits = (
        db.query(AuditEvent)
        .filter(AuditEvent.action == AUDIT_ACTION_OPS_COMPLETED_PARTIAL)
        .all()
    )
    assert any(
        a.request_id == key or (a.metadata_ or {}).get("idempotency_key") == key
        for a in audits
    )


def test_wrong_batch_rejected(db: Session):
    pe, portfolio, batch_id, _, now = _legacy_zombie_fixture(db)
    with _legacy_cleanup_test_patches():
        audit = audit_legacy_bundle_cleanup(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            now=now,
        )
    audit["batch_id"] = str(uuid.uuid4())
    audit["read_model"]["intent_status"] = IntentStatus.PARTIAL.value
    audit["read_model"]["lock"]["zombie"] = True
    with pytest.raises(BundleLegacyCleanupRejected) as exc:
        validate_legacy_cleanup_preconditions(audit)
    assert exc.value.code == "lock_batch_mismatch"


def test_no_confirmed_no_cash_rejected(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    audit = {
        "read_model": {
            "status": STATUS_RECONCILIATION_REQUIRED,
            "intent_status": IntentStatus.PARTIAL.value,
            "lock": {"zombie": True},
            "confirmed_allocations": [],
            "cash_residual_usdc": 0,
        },
        "raw_invest_lock": {"batch_id": batch_id},
        "batch_id": batch_id,
        "live_onchain_submitted": [],
        "ledger_shadow": {"verdict": "MATCH"},
    }
    with pytest.raises(BundleLegacyCleanupRejected) as exc:
        validate_legacy_cleanup_preconditions(audit)
    assert exc.value.code == "no_confirmed_allocation_or_cash"


def test_live_submitted_tx_rejected(db: Session):
    batch_id = str(uuid.uuid4())
    audit = {
        "read_model": {
            "status": STATUS_RECONCILIATION_REQUIRED,
            "intent_status": IntentStatus.PARTIAL.value,
            "lock": {"zombie": True},
            "confirmed_allocations": [{"asset": "CBBTC"}],
            "cash_residual_usdc": 4.2,
        },
        "raw_invest_lock": {"batch_id": batch_id},
        "batch_id": batch_id,
        "live_onchain_submitted": [{"swap_id": "s1", "tx_hash": "0xabc"}],
        "ledger_shadow": {"verdict": "MATCH"},
    }
    with pytest.raises(BundleLegacyCleanupRejected) as exc:
        validate_legacy_cleanup_preconditions(audit)
    assert exc.value.code == "live_onchain_submitted"


def test_pe_positions_unchanged_on_apply(db: Session):
    pe, portfolio, batch_id, _, now = _legacy_zombie_fixture(db)
    pe_before = snapshot_pe_bundle_positions(db, portfolio_id=portfolio.id)

    with _legacy_cleanup_test_patches():
        result = complete_legacy_bundle_with_cash_residual(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            idempotency_key=f"pe-{batch_id}",
            actor_id="test-ops",
            dry_run=False,
            now=now,
        )
        db.commit()

    assert result["pe_unchanged"] is True
    assert snapshot_pe_bundle_positions(db, portfolio_id=portfolio.id) == pe_before


def test_read_model_after_apply_not_zombie(db: Session):
    pe, portfolio, batch_id, _, now = _legacy_zombie_fixture(db)

    with _legacy_cleanup_test_patches():
        complete_legacy_bundle_with_cash_residual(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            idempotency_key=f"rm-{batch_id}",
            actor_id="test-ops",
            dry_run=False,
            now=now,
        )
        db.commit()
        state = build_bundle_reconciliation_state(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            now=now,
        )

    assert state["lock"]["present"] is False
    assert state["lock"]["zombie"] is False
    assert len(state["pending_allocations"]) == 0


def test_plan_documents_no_pe_movement(db: Session):
    pe, portfolio, batch_id, _, now = _legacy_zombie_fixture(db)
    with _legacy_cleanup_test_patches():
        audit = audit_legacy_bundle_cleanup(
            db,
            person_id=pe.person_id,
            portfolio_id=portfolio.id,
            batch_id=batch_id,
            now=now,
        )
        assert audit["read_model"]["status"] == STATUS_RECONCILIATION_REQUIRED
        validate_legacy_cleanup_preconditions(audit)
        plan = plan_legacy_cleanup_writes(
            audit,
            idempotency_key="plan-key",
            actor_id="test",
        )

    assert plan["target"]["pe_positions_mutated"] is False
    assert plan["target"]["spot_sell"] is False
    assert plan["target"]["trading_release"] is False
    assert plan["target"]["cash_residual_preserved_in_bundle"] is True
