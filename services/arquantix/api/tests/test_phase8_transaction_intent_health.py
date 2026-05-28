"""Tests Phase 8 — santé transaction_intents / TTL stale."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_health import (
    classify_stale_intent,
    compute_health_summary,
    list_stale_intents,
    reconcile_stale_intents,
)
from services.transaction_intents.transaction_intent_ttl import ttl_minutes_for_status
from tests.conftest import make_linked_client
from tests.test_phase7_transaction_intents import _migration_166_ready


pytestmark = pytest.mark.skipif(
    not _migration_166_ready(),
    reason="Migration 166 requise.",
)


def _upsert_intent(
    db: Session,
    pe,
    *,
    status: str,
    product_type: str = IntentProductType.LIFI_SWAP.value,
    updated_ago_minutes: int = 120,
) -> TransactionIntent:
    key = f"health-test-{uuid.uuid4().hex[:12]}"
    updated = datetime.now(timezone.utc) - timedelta(minutes=updated_ago_minutes)
    row, _ = TransactionIntentRepository.upsert(
        db,
        person_id=pe.person_id,
        product_type=product_type,
        operation_type="swap",
        idempotency_key=key,
        status=status,
        wallet_address="0xabc",
        chain_id=8453,
    )
    row.updated_at = updated
    row.created_at = updated
    db.add(row)
    db.flush()
    return row


def test_awaiting_signature_stale_detected(db: Session):
    pe = make_linked_client(db)
    row = _upsert_intent(
        db,
        pe,
        status=IntentStatus.AWAITING_SIGNATURE.value,
        updated_ago_minutes=120,
    )
    db.commit()

    stale = classify_stale_intent(row)
    assert stale is not None
    assert stale.discrepancy_type == "intent_awaiting_signature_stale"
    assert stale.product_type == IntentProductType.LIFI_SWAP.value


def test_submitted_stale_detected(db: Session):
    pe = make_linked_client(db)
    row = _upsert_intent(
        db,
        pe,
        status=IntentStatus.SUBMITTED.value,
        updated_ago_minutes=90,
    )
    db.commit()

    stale = classify_stale_intent(row)
    assert stale is not None
    assert "submitted" in stale.discrepancy_type


def test_partial_stale_detected(db: Session):
    pe = make_linked_client(db)
    row = _upsert_intent(
        db,
        pe,
        status=IntentStatus.PARTIAL.value,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        updated_ago_minutes=200,
    )
    db.commit()

    stale = classify_stale_intent(row)
    assert stale is not None
    assert stale.severity == "P1"


def test_confirmed_not_stale(db: Session):
    pe = make_linked_client(db)
    row = _upsert_intent(
        db,
        pe,
        status=IntentStatus.CONFIRMED.value,
        updated_ago_minutes=5000,
    )
    db.commit()

    assert classify_stale_intent(row) is None


def test_health_summary_by_product(db: Session):
    pe = make_linked_client(db)
    _upsert_intent(db, pe, status=IntentStatus.CONFIRMED.value, updated_ago_minutes=10)
    _upsert_intent(
        db,
        pe,
        status=IntentStatus.AWAITING_SIGNATURE.value,
        product_type=IntentProductType.MORPHO_EARN.value,
        updated_ago_minutes=200,
    )
    db.commit()

    summary = compute_health_summary(db)
    assert "by_product" in summary
    assert summary["global"]["total_intents"] >= 2
    lifi = next(
        (p for p in summary["by_product"] if p["product_type"] == IntentProductType.LIFI_SWAP.value),
        None,
    )
    assert lifi is not None
    assert lifi["total"] >= 1


def test_reconcile_stale_dry_run_writes_nothing(db: Session):
    pe = make_linked_client(db)
    _upsert_intent(
        db,
        pe,
        status=IntentStatus.SUBMITTED.value,
        updated_ago_minutes=120,
    )
    db.commit()

    before = db.query(ReconciliationDiscrepancy).count()
    report = reconcile_stale_intents(db, dry_run=True, person_id=pe.person_id)
    db.rollback()
    after = db.query(ReconciliationDiscrepancy).count()

    assert report["dry_run"] is True
    assert report["stale_detected"] >= 1
    assert report["discrepancies_written"] == 0
    assert after == before


def test_reconcile_stale_no_dry_run_creates_discrepancy(db: Session):
    pe = make_linked_client(db)
    row = _upsert_intent(
        db,
        pe,
        status=IntentStatus.AWAITING_SIGNATURE.value,
        updated_ago_minutes=180,
    )
    db.commit()

    report = reconcile_stale_intents(db, dry_run=False, person_id=pe.person_id)
    db.commit()

    assert report["discrepancies_written"] >= 1
    open_rows = DiscrepancyRepository.list_open_for_person(db, pe.person_id)
    types = {r.discrepancy_type for r in open_rows}
    assert "intent_awaiting_signature_stale" in types


def test_no_balance_modification(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())

    reconcile_stale_intents(db, dry_run=False, person_id=pe.person_id)
    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


def test_ttl_policy_defaults():
    assert ttl_minutes_for_status(IntentStatus.AWAITING_SIGNATURE.value) == 60
    assert ttl_minutes_for_status(IntentStatus.SUBMITTED.value) == 45
