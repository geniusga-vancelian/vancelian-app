"""Tests Phase 1 — hardening transaction_intents (read-only / best-effort)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import RawOnChainEvent, TransactionIntent
from services.privy_wallet.enums import PersonWalletDepositStatus
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.webhook_service import PrivyWebhookProcessor
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.ledgity_intent_sync import (
    LEDGITY_PRODUCT,
    ensure_ledgity_intent_for_vault_transaction,
    mark_ledgity_intent_confirmed,
)
from services.transaction_intents.lifi_intent_sync import sync_lifi_swap_intent
from services.transaction_intents.privy_deposit_intent_sync import (
    OBSERVED_EXTERNAL_DEPOSIT_KEY,
    build_observed_external_deposit_classification,
    classify_observed_external_privy_deposit,
    ensure_webapp_privy_deposit_intent,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_health import compute_health_summary
from services.transaction_intents.transaction_intent_reconciliation import (
    build_gap_report_for_person,
    scan_intent_gaps_for_person,
)
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import _seed_wallet
from tests.test_phase7_transaction_intents import _migration_166_ready


def _migration_167_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_intents' "
                    "AND column_name = 'linked_reference_id'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_167_ready(), reason="Migration 167 requise."),
]


def _seed_confirmed_deposit(db: Session, pe, **overrides) -> PersonWalletDeposit:
    wallet = _seed_wallet(db, pe)
    deposit = PersonWalletDeposit(
        person_crypto_wallet_id=wallet.id,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        transaction_kind="privy_deposit_in",
        direction="credit",
        asset="USDC",
        amount=Decimal("100"),
        chain_type="ethereum",
        chain_id=8453,
        tx_hash=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
        log_index=0,
        to_address=wallet.address,
        status=PersonWalletDepositStatus.CONFIRMED.value,
        title="Dépôt USDC",
        subtitle="+100 USDC",
        **overrides,
    )
    db.add(deposit)
    db.flush()
    return deposit


def test_external_privy_webhook_does_not_create_intent(db: Session):
    from tests.test_privy_wallet_deposits import _deposit_payload, _seed_privy_wallet

    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    processor = PrivyWebhookProcessor()
    payload = _deposit_payload(to_address=wallet.address)
    event = processor.store_raw_event(
        db,
        event_type="wallet.funds_deposited",
        payload=payload,
        svix_id=f"msg_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        external_reference=None,
    )
    processor.process_event(db, event)
    db.commit()

    deposit = (
        db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == pe.person_id)
        .order_by(PersonWalletDeposit.created_at.desc())
        .first()
    )
    assert deposit is not None
    assert deposit.privy_webhook_event_id == event.id

    meta = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
    assert meta.get(OBSERVED_EXTERNAL_DEPOSIT_KEY) is True
    assert meta.get("event_source") == "privy_webhook"
    assert meta.get("initiated_by") == "external"
    assert meta.get("transaction_intent_policy") == "none_by_default"

    intent_count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.product_type == IntentProductType.PRIVY_DEPOSIT.value,
        )
        .count()
    )
    assert intent_count == 0


def test_privy_webhook_replay_is_idempotent_without_intent(db: Session):
    from tests.test_privy_wallet_deposits import _deposit_payload, _seed_privy_wallet

    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    processor = PrivyWebhookProcessor()
    payload = _deposit_payload(to_address=wallet.address)
    event = processor.store_raw_event(
        db,
        event_type="wallet.funds_deposited",
        payload=payload,
        svix_id=f"msg_{uuid.uuid4().hex[:8]}",
        idempotency_key=f"idem_{uuid.uuid4().hex[:8]}",
        external_reference=None,
    )
    processor.process_event(db, event)
    db.commit()

    deposit_count_before = (
        db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == pe.person_id)
        .count()
    )

    processor.process_event(db, event)
    db.commit()

    deposit_count_after = (
        db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == pe.person_id)
        .count()
    )
    assert deposit_count_after == deposit_count_before == 1

    intent_count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.product_type == IntentProductType.PRIVY_DEPOSIT.value,
        )
        .count()
    )
    assert intent_count == 0


def test_webapp_privy_deposit_intent_only_when_explicit(db: Session):
    pe = make_linked_client(db)
    deposit = _seed_confirmed_deposit(db, pe)

    assert ensure_webapp_privy_deposit_intent(db, deposit) is None
    assert ensure_webapp_privy_deposit_intent(db, deposit, webapp_initiated=False) is None

    result = ensure_webapp_privy_deposit_intent(db, deposit, webapp_initiated=True)
    db.commit()
    assert result is not None

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_deposits",
        linked_id=deposit.id,
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.PRIVY_DEPOSIT.value


def test_classify_observed_external_privy_deposit(db: Session):
    pe = make_linked_client(db)
    deposit = _seed_confirmed_deposit(db, pe)

    classification = classify_observed_external_privy_deposit(db, deposit)
    db.refresh(deposit)

    assert classification[OBSERVED_EXTERNAL_DEPOSIT_KEY] is True
    meta = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
    assert meta.get("initiated_by") == "external"
    assert build_observed_external_deposit_classification()["transaction_intent_policy"] == "none_by_default"


def test_lifi_approval_persisted_in_audit_and_intent(db: Session):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("9"),
        audit_log=[{"event": "awaiting_signature"}],
    )
    db.add(swap)
    db.flush()

    svc = LifiExecuteService()
    approval_hash = f"0xapprove{uuid.uuid4().hex[:56]}"
    svc.record_token_approval(
        db,
        person_id=pe.person_id,
        swap_id=swap.id,
        tx_hash=approval_hash,
    )
    db.refresh(swap)

    events = [e.get("event") for e in swap.audit_log if isinstance(e, dict)]
    assert "approval_submitted" in events
    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    assert intent is not None
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    assert meta.get("approval_tx_hash") == approval_hash.lower()


def test_ledgity_intent_sync_morpho_model(db: Session):
    pe = make_linked_client(db)
    vault_tx_id = f"cl{uuid.uuid4().hex[:22]}"
    wallet = f"0x{uuid.uuid4().hex[:40]}"

    result = ensure_ledgity_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vault_tx_id,
        vault_address=f"0x{uuid.uuid4().hex[:40]}",
        chain_id=8453,
        wallet_address=wallet,
        operation="deposit",
        idempotency_key=f"ledgity-{uuid.uuid4().hex[:8]}",
        tx_index=0,
    )
    db.commit()
    assert result is not None

    mark_ledgity_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vault_tx_id,
        tx_hash=f"0x{uuid.uuid4().hex}",
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_vault_transaction(
        db,
        vault_transaction_id=vault_tx_id,
        person_id=pe.person_id,
    )
    assert intent is not None
    assert intent.product_type == LEDGITY_PRODUCT
    assert intent.status == IntentStatus.CONFIRMED.value


def test_health_summary_excludes_dormant_privy_deposit(db: Session):
    summary = compute_health_summary(db)
    product_types = {row["product_type"] for row in summary["by_product"]}
    assert IntentProductType.PRIVY_DEPOSIT.value not in product_types
    assert IntentProductType.LEDGITY_VAULT.value in product_types
    assert IntentProductType.BUNDLE_WITHDRAW.value in product_types


def test_gap_report_does_not_flag_external_deposit_without_intent(db: Session):
    pe = make_linked_client(db)
    deposit = _seed_confirmed_deposit(
        db,
        pe,
        metadata_json=build_observed_external_deposit_classification(),
    )
    db.commit()

    report = build_gap_report_for_person(db, pe.person_id)
    assert not report["gaps"]["privy_deposits_without_tx_hash"]
    all_types = {
        row.get("discrepancy_type") for bucket in report["gaps"].values() for row in bucket
    }
    assert "deposit_without_intent" not in all_types


def test_gap_report_flags_deposit_without_webhook_source(db: Session):
    pe = make_linked_client(db)
    _seed_confirmed_deposit(
        db,
        pe,
        metadata_json=build_observed_external_deposit_classification(),
    )
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    types = {g["discrepancy_type"] for g in gaps}
    assert "privy_deposit_without_webhook_source" in types


def test_gap_report_flags_deposit_without_raw_event_after_ttl(db: Session, monkeypatch):
    monkeypatch.setenv("PRIVY_DEPOSIT_RAW_EVENT_TTL_HOURS", "1")
    pe = make_linked_client(db)
    old = datetime.now(timezone.utc) - timedelta(hours=6)
    _seed_confirmed_deposit(
        db,
        pe,
        confirmed_at=old,
        created_at=old,
        metadata_json=build_observed_external_deposit_classification(),
    )
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    types = {g["discrepancy_type"] for g in gaps}
    assert "privy_deposit_without_raw_onchain_event" in types


def test_gap_report_detects_lifi_missing_approval(db: Session):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        tx_hash=f"0x{uuid.uuid4().hex}",
        audit_log=[{"event": "token_approval_required"}, {"event": "submitted"}],
    )
    db.add(swap)
    db.flush()
    sync_lifi_swap_intent(db, swap, status=IntentStatus.SUBMITTED.value)
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    types = {g["discrepancy_type"] for g in gaps}
    assert "lifi_swap_missing_approval_hash" in types
