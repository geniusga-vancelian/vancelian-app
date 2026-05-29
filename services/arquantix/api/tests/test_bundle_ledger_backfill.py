"""Tests Phase 4B — backfill idempotent bundle ledger."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_ledger.backfill import plan_backfill, run_backfill
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


def _audit_fund(db: Session, *, pe, portfolio, batch_id: str, amount: str = "50") -> AuditEvent:
    row = AuditEvent(
        id=uuid.uuid4(),
        entity_type="portfolio",
        entity_id=str(portfolio.id),
        action="bundle.fund_cash_leg",
        actor_id=f"bundle-funding:{batch_id}",
        metadata_={
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "batch_id": batch_id,
            "entry_asset": "USDC",
            "amount": amount,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def _audit_release(db: Session, *, pe, portfolio, batch_id: str, amount: str = "20") -> AuditEvent:
    row = AuditEvent(
        id=uuid.uuid4(),
        entity_type="portfolio",
        entity_id=str(portfolio.id),
        action="bundle.release_cash_leg",
        actor_id=f"bundle-funding:{batch_id}",
        metadata_={
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "batch_id": batch_id,
            "entry_asset": "USDC",
            "amount": amount,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str, action: str = "allocation"):
    return [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": batch_id,
            "bundle_action": action,
            "leg_action": action,
            "leg_id": "leg-backfill-1",
        },
        {"event": "bundle_pe_atoms_applied", "leg_id": "leg-backfill-1"},
    ]


def test_backfill_deposit_from_pe_audit_event(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    _audit_fund(db, pe=pe, portfolio=portfolio, batch_id=batch_id)
    db.flush()

    result = run_backfill(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        dry_run=False,
    )
    db.flush()

    assert len(result.applied) == 1
    rows = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
            BundleLedgerEntry.event_type == "BUNDLE_DEPOSIT",
        )
        .all()
    )
    assert len(rows) == 1
    assert rows[0].batch_id == batch_id


def test_backfill_withdrawal_from_pe_audit_event(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    _audit_release(db, pe=pe, portfolio=portfolio, batch_id=batch_id, amount="30")
    db.flush()

    result = run_backfill(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        dry_run=False,
    )
    db.flush()

    assert len(result.applied) == 1
    row = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.event_type == "BUNDLE_WITHDRAWAL",
            BundleLedgerEntry.batch_id == batch_id,
        )
        .first()
    )
    assert row is not None
    assert row.quantity == Decimal("30")


def test_backfill_allocation_from_confirmed_lifi_swap(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("25"),
        estimated_receive=Decimal("0.0002"),
        tx_hash=f"0x{uuid.uuid4().hex}",
        confirmed_at=datetime.now(timezone.utc),
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    db.add(swap)
    from tests.test_bundle_ledger_reconciliation import _instrument_cbbtc
    _instrument_cbbtc(db)
    _instrument_usdc(db)
    db.flush()

    result = run_backfill(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        dry_run=False,
    )
    db.flush()

    assert len(result.applied) >= 1
    buys = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.event_type == "BUNDLE_ALLOCATION_BUY")
        .all()
    )
    assert len(buys) == 1


def test_backfill_idempotent(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    _audit_fund(db, pe=pe, portfolio=portfolio, batch_id=batch_id)
    db.flush()

    first = run_backfill(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, dry_run=False,
    )
    second = run_backfill(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, dry_run=False,
    )
    db.flush()

    assert len(first.applied) == 1
    assert len(second.applied) == 0
    assert len(second.skipped_existing) >= 1
    count = db.query(BundleLedgerEntry).filter(
        BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
    ).count()
    assert count == 1


def test_backfill_dry_run_does_not_write(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    _audit_fund(db, pe=pe, portfolio=portfolio, batch_id=batch_id)
    db.flush()

    before = db.query(BundleLedgerEntry).count()
    plan = plan_backfill(
        db, person_id=pe.person_id, portfolio_id=portfolio.id,
    )
    after = db.query(BundleLedgerEntry).count()

    assert len(plan.planned) == 1
    assert before == after


def test_backfill_skips_mirror_written_deposit(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("86"))
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("40"),
        batch_id=batch_id,
    )
    db.flush()

    result = run_backfill(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, dry_run=False,
    )
    assert len(result.applied) == 0
    assert len(result.skipped_existing) >= 1
