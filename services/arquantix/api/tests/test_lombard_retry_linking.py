"""Tests Phase 3B-R3 — Lombard logical_borrow_id + retry linking."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from services.transaction_intents.enums import IntentStatus
from services.transaction_intents.lombard_intent_sync import (
    STEP_CONFIRMED,
    STEP_FAILED,
    ensure_lombard_parent_intent,
    mark_lombard_step_confirmed,
    sync_lombard_step_from_ledger_receipt,
)
from services.transaction_intents.lombard_retry_linking import (
    LOMBARD_MAX_RETRY_ATTEMPTS,
    LombardRetryLinkError,
    project_lombard_logical_borrow_group,
    project_lombard_logical_borrow_terminal_status,
    resolve_lombard_prepare_link_metadata,
)
from services.transaction_intents.repository import TransactionIntentRepository
from tests.conftest import make_linked_client
from tests.test_phase7_transaction_intents import _migration_166_ready
from tests.test_phase7c_lombard_transaction_intents import _group_key, _prepare_parent, _vault_id

pytestmark = pytest.mark.skipif(
    not _migration_166_ready(),
    reason="Migration 166 requise.",
)


def _set_retryable_failed_initial(db: Session, pe, gk: str, market: str, ledger_ids: list[str]) -> None:
    mark_lombard_step_confirmed(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        ledger_entry_id=ledger_ids[0],
        receipt_status="success",
    )
    sync_lombard_step_from_ledger_receipt(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        ledger_entry_id=ledger_ids[2],
        tx_hash=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}",
        ledger_status="reverted",
    )
    db.commit()


def test_initial_prepare_creates_logical_borrow_id_and_attempt_zero(db: Session):
    pe = make_linked_client(db)
    gk, market, _ledger_ids = _prepare_parent(db, pe)

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    meta = intent.metadata_json or {}
    assert meta.get("logical_borrow_id")
    assert meta.get("retry_attempt_number") == 0
    assert meta.get("max_retry_attempts") == LOMBARD_MAX_RETRY_ATTEMPTS
    assert meta.get("retry_of_group_key") is None


def test_retry_prepare_links_logical_borrow_and_retry_of_group_key(db: Session):
    pe = make_linked_client(db)
    initial_gk, market, ledger_ids = _prepare_parent(db, pe)
    _set_retryable_failed_initial(db, pe, initial_gk, market, ledger_ids)

    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    logical_id = initial.metadata_json["logical_borrow_id"]
    retry_gk = _group_key()
    retry_ledger = [_vault_id()]

    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        wallet_address=initial.wallet_address,
        chain_id=8453,
        steps=[{"step": "open_loan", "tx_index": 0, "ledger_entry_id": retry_ledger[0]}],
        logical_borrow_id=logical_id,
        retry_of_group_key=initial_gk,
        retry_attempt_number=1,
    )
    db.commit()

    retry_intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=retry_gk, market_or_vault=market
    )
    assert retry_intent.metadata_json.get("logical_borrow_id") == logical_id
    assert retry_intent.metadata_json.get("retry_of_group_key") == initial_gk
    assert retry_intent.metadata_json.get("retry_attempt_number") == 1


def test_retry_success_supersedes_initial_intent(db: Session):
    pe = make_linked_client(db)
    initial_gk, market, ledger_ids = _prepare_parent(db, pe)
    _set_retryable_failed_initial(db, pe, initial_gk, market, ledger_ids)

    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    logical_id = initial.metadata_json["logical_borrow_id"]
    retry_gk = _group_key()
    retry_ledger = [_vault_id()]

    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        wallet_address=initial.wallet_address,
        chain_id=8453,
        steps=[{"step": "open_loan", "tx_index": 0, "ledger_entry_id": retry_ledger[0]}],
        logical_borrow_id=logical_id,
        retry_of_group_key=initial_gk,
        retry_attempt_number=1,
    )
    mark_lombard_step_confirmed(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        ledger_entry_id=retry_ledger[0],
        receipt_status="success",
    )
    db.commit()

    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    retry_intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=retry_gk, market_or_vault=market
    )
    assert retry_intent.status == IntentStatus.CONFIRMED.value
    assert initial.status == IntentStatus.SUPERSEDED.value
    assert initial.metadata_json.get("superseded_by_group_key") == retry_gk
    assert initial.metadata_json.get("terminal_outcome") == "borrow_not_opened"


def test_superseded_initial_keeps_open_loan_failed_step_history(db: Session):
    pe = make_linked_client(db)
    initial_gk, market, ledger_ids = _prepare_parent(db, pe)
    _set_retryable_failed_initial(db, pe, initial_gk, market, ledger_ids)

    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    logical_id = initial.metadata_json["logical_borrow_id"]
    retry_gk = _group_key()
    retry_ledger = [_vault_id()]

    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        wallet_address=initial.wallet_address,
        chain_id=8453,
        steps=[{"step": "open_loan", "tx_index": 0, "ledger_entry_id": retry_ledger[0]}],
        logical_borrow_id=logical_id,
        retry_of_group_key=initial_gk,
        retry_attempt_number=1,
    )
    mark_lombard_step_confirmed(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        ledger_entry_id=retry_ledger[0],
        receipt_status="success",
    )
    db.commit()

    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    steps = initial.metadata_json.get("steps") or []
    open_loan = next(s for s in steps if s.get("step") == "open_loan")
    assert open_loan.get("status") == STEP_FAILED
    approve = next(s for s in steps if s.get("step") == "approve")
    assert approve.get("status") == STEP_CONFIRMED


def test_max_retry_attempts_blocks_second_retry_prepare(db: Session):
    pe = make_linked_client(db)
    initial_gk, market, ledger_ids = _prepare_parent(db, pe)
    _set_retryable_failed_initial(db, pe, initial_gk, market, ledger_ids)
    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    logical_id = initial.metadata_json["logical_borrow_id"]

    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=_group_key(),
        market_or_vault=market,
        wallet_address=initial.wallet_address,
        chain_id=8453,
        steps=[{"step": "open_loan", "tx_index": 0, "ledger_entry_id": _vault_id()}],
        logical_borrow_id=logical_id,
        retry_of_group_key=initial_gk,
        retry_attempt_number=1,
    )
    db.commit()

    with pytest.raises(LombardRetryLinkError, match="retry already attempted"):
        resolve_lombard_prepare_link_metadata(
            db,
            person_id=pe.person_id,
            market_or_vault=market,
            logical_borrow_id=logical_id,
            retry_of_group_key=initial_gk,
            retry_attempt_number=1,
        )


def test_confirmed_initial_without_retry_unchanged(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)
    for lid in ledger_ids:
        mark_lombard_step_confirmed(
            db,
            person_id=pe.person_id,
            group_key=gk,
            market_or_vault=market,
            ledger_entry_id=lid,
            receipt_status="success",
        )
    db.commit()

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    assert intent.status == IntentStatus.CONFIRMED.value
    assert intent.metadata_json.get("retry_of_group_key") is None


def test_projection_returns_confirmed_when_retry_success(db: Session):
    pe = make_linked_client(db)
    initial_gk, market, ledger_ids = _prepare_parent(db, pe)
    _set_retryable_failed_initial(db, pe, initial_gk, market, ledger_ids)
    initial = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=initial_gk, market_or_vault=market
    )
    logical_id = initial.metadata_json["logical_borrow_id"]
    retry_gk = _group_key()
    retry_ledger = [_vault_id()]

    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        wallet_address=initial.wallet_address,
        chain_id=8453,
        steps=[{"step": "open_loan", "tx_index": 0, "ledger_entry_id": retry_ledger[0]}],
        logical_borrow_id=logical_id,
        retry_of_group_key=initial_gk,
        retry_attempt_number=1,
    )
    mark_lombard_step_confirmed(
        db,
        person_id=pe.person_id,
        group_key=retry_gk,
        market_or_vault=market,
        ledger_entry_id=retry_ledger[0],
        receipt_status="success",
    )
    db.commit()

    projection = project_lombard_logical_borrow_group(
        db, person_id=pe.person_id, logical_borrow_id=logical_id
    )
    assert projection["terminal_status"] == IntentStatus.CONFIRMED.value
    assert len(projection["intents"]) == 2


def test_project_terminal_status_unit():
    intents = [
        {"status": "retryable_failed", "metadata_json": {"retry_attempt_number": 0}},
        {"status": "confirmed", "metadata_json": {"retry_attempt_number": 1}},
    ]
    assert project_lombard_logical_borrow_terminal_status(intents) == IntentStatus.CONFIRMED.value
