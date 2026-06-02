"""Tests Phase 7C — transaction_intents / Lombard Borrow."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.lombard_intent_sync import (
    LOMBARD_LINKED_TABLE,
    LOMBARD_TERMINAL_OUTCOME_BORROW_NOT_OPENED,
    STEP_CONFIRMED,
    STEP_FAILED,
    STEP_PENDING,
    ensure_lombard_parent_intent,
    is_lombard_retryable_failed,
    lombard_auth_prerequisite_confirmed,
    lombard_parent_intent_key,
    mark_lombard_intent_failed_final,
    mark_lombard_intent_superseded,
    mark_lombard_step_confirmed,
    mark_lombard_step_failed,
    recompute_lombard_parent_status,
    sync_lombard_step_from_ledger_receipt,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_reconciliation import scan_intent_gaps_for_person
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import _seed_wallet
from tests.test_phase7_transaction_intents import _migration_166_ready


def _vault_table_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'onchain_vault_transactions'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_166_ready(),
    reason="Migration 166 requise.",
)


def _group_key() -> str:
    return f"lombard-test-{uuid.uuid4().hex[:16]}"


def _vault_id() -> str:
    return f"cl{uuid.uuid4().hex[:22]}"


def _prepare_parent(db: Session, pe, *, group_key: str | None = None) -> tuple[str, str, list[str]]:
    wallet = _seed_wallet(db, pe)
    market = "0xmarket00000000000000000000000000000001"
    gk = group_key or _group_key()
    ledger_ids = [_vault_id(), _vault_id(), _vault_id()]
    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        wallet_address=wallet.address,
        chain_id=8453,
        steps=[
            {"step": "approve", "tx_index": 0, "ledger_entry_id": ledger_ids[0]},
            {"step": "authorize", "tx_index": 1, "ledger_entry_id": ledger_ids[1]},
            {"step": "open_loan", "tx_index": 0, "ledger_entry_id": ledger_ids[2]},
        ],
    )
    db.commit()
    return gk, market, ledger_ids


def test_lombard_prepare_creates_parent_with_steps(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.LOMBARD_BORROW.value
    assert intent.operation_type == "borrow"
    assert intent.status == IntentStatus.AWAITING_SIGNATURE.value
    assert intent.linked_table == LOMBARD_LINKED_TABLE
    assert intent.linked_reference_id == gk
    steps = intent.metadata_json.get("steps", [])
    assert len(steps) == 3
    assert all(s.get("status") == STEP_PENDING for s in steps)
    assert {s["ledger_entry_id"] for s in steps} == set(ledger_ids)


def test_lombard_confirm_step_success_sets_confirmed(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)
    tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    sync_lombard_step_from_ledger_receipt(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        ledger_entry_id=ledger_ids[0],
        tx_hash=tx,
        ledger_status="success",
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    step = next(s for s in intent.metadata_json["steps"] if s["ledger_entry_id"] == ledger_ids[0])
    assert step["status"] == STEP_CONFIRMED
    assert step["tx_hash"] == tx.lower()


def test_lombard_confirm_step_failed_sets_failed(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)

    mark_lombard_step_failed(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        ledger_entry_id=ledger_ids[1],
        receipt_status="reverted",
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    step = next(s for s in intent.metadata_json["steps"] if s["ledger_entry_id"] == ledger_ids[1])
    assert step["status"] == STEP_FAILED


def test_lombard_parent_confirmed_when_all_steps_confirmed(db: Session):
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


def test_lombard_parent_partial_on_mix(db: Session):
    steps = [
        {"step": "approve", "status": STEP_CONFIRMED},
        {"step": "authorize", "status": STEP_FAILED},
        {"step": "open_loan", "status": STEP_PENDING},
    ]
    assert recompute_lombard_parent_status(steps) == IntentStatus.PARTIAL.value


def test_lombard_retryable_failed_when_approve_confirmed_open_loan_failed():
    steps = [
        {"step": "approve", "status": STEP_CONFIRMED, "ledger_entry_id": "a1"},
        {"step": "open_loan", "status": STEP_FAILED, "ledger_entry_id": "a2"},
    ]
    assert is_lombard_retryable_failed(steps) is True
    assert recompute_lombard_parent_status(steps) == IntentStatus.RETRYABLE_FAILED.value


def test_lombard_open_loan_failed_without_auth_confirmed_is_failed_not_retryable():
    steps = [
        {"step": "approve", "status": STEP_PENDING, "ledger_entry_id": "a1"},
        {"step": "open_loan", "status": STEP_FAILED, "ledger_entry_id": "a2"},
    ]
    assert lombard_auth_prerequisite_confirmed(steps) is False
    assert is_lombard_retryable_failed(steps) is False
    assert recompute_lombard_parent_status(steps) == IntentStatus.FAILED.value


def test_lombard_open_loan_only_success_stays_confirmed():
    steps = [{"step": "open_loan", "status": STEP_CONFIRMED, "ledger_entry_id": "a1"}]
    assert recompute_lombard_parent_status(steps) == IntentStatus.CONFIRMED.value


def test_lombard_open_loan_only_failed_is_failed():
    steps = [{"step": "open_loan", "status": STEP_FAILED, "ledger_entry_id": "a1"}]
    assert recompute_lombard_parent_status(steps) == IntentStatus.FAILED.value


def test_lombard_retryable_failed_sets_terminal_metadata(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)
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

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    assert intent.status == IntentStatus.RETRYABLE_FAILED.value
    assert intent.metadata_json.get("lombard_status_detail") == "retryable_failed"
    assert intent.metadata_json.get("terminal_outcome") == LOMBARD_TERMINAL_OUTCOME_BORROW_NOT_OPENED


def test_lombard_mark_superseded_and_failed_final_helpers(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)

    superseded = mark_lombard_intent_superseded(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        superseded_by_group_key="retry-group-key",
        superseded_by_intent_id=str(uuid.uuid4()),
    )
    db.commit()
    assert superseded is not None
    assert superseded["status"] == IntentStatus.SUPERSEDED.value

    failed_final = mark_lombard_intent_failed_final(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        reason="retry_exhausted",
    )
    db.commit()
    assert failed_final is not None
    assert failed_final["status"] == IntentStatus.FAILED_FINAL.value


def test_lombard_parent_failed_when_all_failed(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)
    for lid in ledger_ids:
        mark_lombard_step_failed(
            db,
            person_id=pe.person_id,
            group_key=gk,
            market_or_vault=market,
            ledger_entry_id=lid,
        )
    db.commit()

    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    assert intent.status == IntentStatus.FAILED.value


def test_lombard_idempotency_same_group(db: Session):
    pe = make_linked_client(db)
    gk, market, ledger_ids = _prepare_parent(db, pe)
    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=market,
        wallet_address="0xabc",
        chain_id=8453,
        steps=[
            {"step": "approve", "tx_index": 0, "ledger_entry_id": ledger_ids[0]},
            {"step": "open_loan", "tx_index": 0, "ledger_entry_id": ledger_ids[2]},
        ],
    )
    db.commit()

    key = lombard_parent_intent_key(
        person_id=pe.person_id, market_or_vault=market, idempotency_key=gk
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


def test_lombard_intent_sync_failure_does_not_raise(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(
        TransactionIntentRepository,
        "upsert",
        MagicMock(side_effect=RuntimeError("intent down")),
    )
    result = ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=_group_key(),
        market_or_vault="0xmarket",
        wallet_address="0xwallet",
        chain_id=8453,
        steps=[{"step": "approve", "tx_index": 0, "ledger_entry_id": _vault_id()}],
    )
    assert result is None


def test_lombard_no_balance_modification(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())
    _prepare_parent(db, pe)
    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_reconciliation_lombard_group_without_intent(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    gk = _group_key()
    vault = "0xmarket00000000000000000000000000000002"
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status,
                idempotency_key, integration_mode, tx_index, group_key, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                'deposit', '1000000', 'USDC', 6, 'pending',
                :idem, 'lombard_v1', 0, :idem, NOW(), NOW()
            )
            """
        ),
        {
            "id": _vault_id(),
            "person_id": str(pe.person_id),
            "vault": vault,
            "wallet": wallet.address.lower(),
            "idem": gk,
        },
    )
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(g["discrepancy_type"] == "lombard_group_without_parent_intent" for g in gaps)


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_reconciliation_parent_confirmed_step_not_confirmed(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    gk = _group_key()
    vault = "0xmarket00000000000000000000000000000003"
    lid = _vault_id()
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status,
                idempotency_key, integration_mode, tx_index, group_key, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                'approve', '0', 'USDC', 6, 'pending',
                :idem, 'lombard_v1', 0, :idem, NOW(), NOW()
            )
            """
        ),
        {
            "id": lid,
            "person_id": str(pe.person_id),
            "vault": vault,
            "wallet": wallet.address.lower(),
            "idem": gk,
        },
    )
    ensure_lombard_parent_intent(
        db,
        person_id=pe.person_id,
        group_key=gk,
        market_or_vault=vault,
        wallet_address=wallet.address,
        chain_id=8453,
        steps=[{"step": "approve", "tx_index": 0, "ledger_entry_id": lid}],
    )
    intent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=vault
    )
    intent.status = IntentStatus.CONFIRMED.value
    db.add(intent)
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(
        g["discrepancy_type"] == "lombard_parent_confirmed_step_not_confirmed" for g in gaps
    )
