"""Tests Phase 7D — transaction_intents / Bundle invest."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.bundle_intent_sync import (
    BUNDLE_LINKED_TABLE,
    LEG_CONFIRMED,
    LEG_FAILED,
    LEG_PENDING,
    LEG_SUBMITTED,
    bundle_parent_intent_key,
    ensure_bundle_parent_intent,
    mark_bundle_leg_confirmed,
    mark_bundle_leg_failed,
    mark_bundle_leg_submitted,
    recompute_bundle_parent_status,
    register_bundle_leg,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_reconciliation import scan_intent_gaps_for_person
from tests.conftest import make_linked_client
from tests.test_phase7_transaction_intents import _migration_166_ready


pytestmark = pytest.mark.skipif(
    not _migration_166_ready(),
    reason="Migration 166 requise.",
)


def _batch_id() -> str:
    return str(uuid.uuid4())


def _bundle_id() -> str:
    return str(uuid.uuid4())


def _prepare_bundle(db: Session, pe) -> tuple[str, str, str]:
    batch_id = _batch_id()
    bundle_id = _bundle_id()
    leg_id = f"bundle-alloc-{batch_id}-ETH"
    swap_id = str(uuid.uuid4())
    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )
    register_bundle_leg(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        leg_id=leg_id,
        swap_id=swap_id,
        asset="ETH",
        target_weight=0.5,
    )
    db.commit()
    return batch_id, bundle_id, swap_id


def test_bundle_start_creates_parent_intent(db: Session):
    pe = make_linked_client(db)
    batch_id = _batch_id()
    bundle_id = _bundle_id()

    ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.BUNDLE_INVEST.value
    assert intent.operation_type == "invest"
    assert intent.status == IntentStatus.AWAITING_SIGNATURE.value
    assert intent.linked_table == BUNDLE_LINKED_TABLE
    assert intent.linked_reference_id == batch_id
    assert intent.metadata_json.get("legs") == []


def test_register_bundle_leg_adds_metadata(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    legs = intent.metadata_json["legs"]
    assert len(legs) == 1
    assert legs[0]["swap_id"] == swap_id
    assert legs[0]["status"] == LEG_PENDING
    assert legs[0]["asset"] == "ETH"


def test_bundle_leg_submitted_sets_tx_hash(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)
    tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    mark_bundle_leg_submitted(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        swap_id=uuid.UUID(swap_id),
        tx_hash=tx,
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    leg = intent.metadata_json["legs"][0]
    assert leg["status"] == LEG_SUBMITTED
    assert leg["tx_hash"] == tx.lower()


def test_bundle_leg_confirmed(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)

    mark_bundle_leg_confirmed(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        swap_id=uuid.UUID(swap_id),
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    assert intent.metadata_json["legs"][0]["status"] == LEG_CONFIRMED


def test_bundle_leg_failed(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)

    mark_bundle_leg_failed(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        swap_id=uuid.UUID(swap_id),
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    assert intent.metadata_json["legs"][0]["status"] == LEG_FAILED


def test_bundle_parent_confirmed_all_legs(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)
    swap_id2 = str(uuid.uuid4())
    register_bundle_leg(
        db,
        person_id=pe.person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        leg_id=f"leg-2-{batch_id}",
        swap_id=swap_id2,
        asset="BTC",
    )
    mark_bundle_leg_confirmed(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id, swap_id=uuid.UUID(swap_id)
    )
    mark_bundle_leg_confirmed(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id, swap_id=uuid.UUID(swap_id2)
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    assert intent.status == IntentStatus.CONFIRMED.value


def test_bundle_parent_partial_mix(db: Session):
    legs = [
        {"leg_id": "a", "status": LEG_CONFIRMED},
        {"leg_id": "b", "status": LEG_PENDING},
    ]
    assert recompute_bundle_parent_status(legs) == IntentStatus.PARTIAL.value


def test_bundle_parent_failed_no_confirmed(db: Session):
    legs = [
        {"leg_id": "a", "status": LEG_FAILED},
        {"leg_id": "b", "status": LEG_FAILED},
    ]
    assert recompute_bundle_parent_status(legs) == IntentStatus.FAILED.value


def test_bundle_idempotency_same_batch(db: Session):
    pe = make_linked_client(db)
    batch_id = _batch_id()
    bundle_id = _bundle_id()
    ensure_bundle_parent_intent(db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id)
    ensure_bundle_parent_intent(db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id)
    db.commit()

    key = bundle_parent_intent_key(
        person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.idempotency_key == key,
        )
        .count()
    )
    assert count == 1


def test_bundle_sync_failure_does_not_raise(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(
        TransactionIntentRepository,
        "upsert",
        MagicMock(side_effect=RuntimeError("intent down")),
    )
    result = ensure_bundle_parent_intent(
        db,
        person_id=pe.person_id,
        bundle_id=_bundle_id(),
        batch_id=_batch_id(),
    )
    assert result is None


def test_bundle_no_balance_modification(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())
    _prepare_bundle(db, pe)
    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


def test_reconciliation_bundle_batch_without_intent(db: Session):
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap

    pe = make_linked_client(db)
    batch_id = _batch_id()
    bundle_id = _bundle_id()
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=10,
        estimated_receive=9,
        audit_log=[
            {
                "event": "bundle_leg_context",
                "batch_id": batch_id,
                "portfolio_id": bundle_id,
                "leg_id": f"bundle-alloc-{batch_id}-ETH",
                "bundle_execution": True,
            }
        ],
    )
    db.add(swap)
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(g["discrepancy_type"] == "bundle_batch_without_parent_intent" for g in gaps)


def test_reconciliation_parent_confirmed_leg_not_confirmed(db: Session):
    pe = make_linked_client(db)
    batch_id, bundle_id, swap_id = _prepare_bundle(db, pe)
    intent = TransactionIntentRepository.find_by_bundle_batch(
        db, person_id=pe.person_id, bundle_id=bundle_id, batch_id=batch_id
    )
    intent.status = IntentStatus.CONFIRMED.value
    db.add(intent)
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(
        g["discrepancy_type"] == "bundle_parent_confirmed_leg_not_confirmed" for g in gaps
    )
