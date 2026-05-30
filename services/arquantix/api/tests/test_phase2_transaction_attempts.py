"""Tests Phase 2 — onchain_transaction_attempts (dual-write, idempotence, gaps)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.transaction_attempts.dual_write import (
    dual_write_lifi_approval_submitted,
    dual_write_lifi_swap_submitted,
    dual_write_vault_step,
)
from services.transaction_attempts.enums import AttemptProtocol, AttemptStepType
from services.transaction_attempts.models import OnchainTransactionAttempt
from services.transaction_attempts.repository import OnchainTransactionAttemptRepository
from services.transaction_attempts.schemas import AttemptCreateInput
from services.transaction_attempts.service import OnchainTransactionAttemptService
from services.transaction_intents.enums import IntentProductType
from services.transaction_intents.lifi_intent_sync import LINKED_TABLE, on_swap_created
from services.transaction_intents.lombard_intent_sync import (
    ensure_lombard_parent_intent,
    sync_lombard_step_from_ledger_receipt,
)
from services.transaction_intents.privy_deposit_intent_sync import (
    OBSERVED_EXTERNAL_DEPOSIT_KEY,
    classify_observed_external_privy_deposit,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_attempts.reconciliation import (
    build_backfill_plan,
    build_backfill_report,
    build_gap_report,
    group_legacy_records_by_chain_tx,
    migration_171_ready,
    scan_attempt_gaps_for_person,
    tx_hash_backfill_idempotency_key,
)
from tests.conftest import make_linked_client
from tests.test_phase1_transaction_intent_hardening import _seed_confirmed_deposit
from tests.test_phase4_reconciliation import _seed_wallet
from tests.test_phase7_transaction_intents import _migration_166_ready, _seed_swap


def _migration_171_ready() -> bool:
    return migration_171_ready()


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_171_ready(), reason="Migration 171 requise."),
]


def test_attempt_idempotency_key_plus_step_type(db: Session):
    pe = make_linked_client(db)
    idem = f"test-idem-{uuid.uuid4().hex[:12]}"
    payload = AttemptCreateInput(
        person_id=pe.person_id,
        chain_id=8453,
        protocol=AttemptProtocol.LIFI.value,
        operation_type="swap",
        step_type=AttemptStepType.SWAP.value,
        idempotency_key=idem,
        group_key="g1",
    )
    first = OnchainTransactionAttemptService.create_prepared_attempt(db, payload)
    second = OnchainTransactionAttemptService.create_prepared_attempt(db, payload)
    db.commit()

    assert first["id"] == second["id"]
    count = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.idempotency_key == idem,
            OnchainTransactionAttempt.step_type == AttemptStepType.SWAP.value,
        )
        .count()
    )
    assert count == 1


def test_lifi_approve_and_swap_attempts_share_intent(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.AWAITING_SIGNATURE.value)
    on_swap_created(db, swap)
    db.flush()

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent is not None

    approval_tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    swap_tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    swap.audit_log = [{"event": "approval_submitted", "tx_hash": approval_tx}]

    dual_write_lifi_approval_submitted(db, swap, approval_tx_hash=approval_tx, intent_id=intent.id)
    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap_tx, intent_id=intent.id)
    db.commit()

    approve = OnchainTransactionAttemptRepository.find_by_composite_key(
        db,
        idempotency_key=f"lifi:{swap.id}:approve",
        step_type=AttemptStepType.APPROVE.value,
    )
    swap_attempt = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == swap_tx.lower(),
            OnchainTransactionAttempt.step_type == AttemptStepType.SWAP.value,
        )
        .first()
    )
    assert approve is not None
    assert swap_attempt is not None
    assert str(approve.intent_id) == str(intent.id)
    assert str(swap_attempt.intent_id) == str(intent.id)
    assert approve.group_key == swap_attempt.group_key == str(swap.id)


def test_vault_approve_and_deposit_share_group_key(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    group_key = f"morpho-grp-{uuid.uuid4().hex[:10]}"
    approve_id = f"cl{uuid.uuid4().hex[:22]}"
    deposit_id = f"cl{uuid.uuid4().hex[:22]}"
    tx_approve = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    tx_deposit = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    dual_write_vault_step(
        db,
        person_id=pe.person_id,
        vault_transaction_id=approve_id,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="approve",
        group_key=group_key,
        step_index=0,
        integration_mode="direct_morpho",
        tx_hash=tx_approve,
        vault_status="success",
    )
    dual_write_vault_step(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_id,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        group_key=group_key,
        step_index=1,
        integration_mode="direct_morpho",
        tx_hash=tx_deposit,
        vault_status="success",
    )
    db.commit()

    attempts = OnchainTransactionAttemptRepository.list_by_group_key(
        db, person_id=pe.person_id, group_key=group_key
    )
    assert len(attempts) == 2
    assert {a.step_type for a in attempts} == {
        AttemptStepType.APPROVE.value,
        AttemptStepType.DEPOSIT.value,
    }
    assert all(a.group_key == group_key for a in attempts)
    assert attempts[0].step_index <= attempts[1].step_index


def test_lombard_multi_step_ordering(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    market = "0xmarket00000000000000000000000000000001"
    gk = f"lombard-test-{uuid.uuid4().hex[:16]}"
    ledger_ids = [f"cl{uuid.uuid4().hex[:22]}" for _ in range(3)]

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
    db.flush()

    for i, lid in enumerate(ledger_ids):
        sync_lombard_step_from_ledger_receipt(
            db,
            person_id=pe.person_id,
            group_key=gk,
            market_or_vault=market,
            ledger_entry_id=lid,
            tx_hash=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}",
            ledger_status="success",
        )
    db.commit()

    attempts = OnchainTransactionAttemptRepository.list_by_group_key(
        db, person_id=pe.person_id, group_key=gk
    )
    assert len(attempts) == 3
    step_types = [a.step_type for a in attempts]
    assert step_types == [
        AttemptStepType.APPROVE.value,
        AttemptStepType.AUTHORIZE.value,
        AttemptStepType.OPEN_LOAN.value,
    ]
    assert attempts[0].protocol == AttemptProtocol.LOMBARD.value


def test_bundle_internal_swap_uses_internal_bundle_protocol(db: Session):
    pe = make_linked_client(db)
    portfolio_id = str(uuid.uuid4())
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="WETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.004"),
        tx_hash=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}",
        audit_log=[
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "portfolio_id": portfolio_id,
                "batch_id": "batch-1",
                "bundle_action": "allocation",
            }
        ],
    )
    db.add(swap)
    db.flush()

    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap.tx_hash)
    db.commit()

    attempt = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == swap.tx_hash.lower(),
            OnchainTransactionAttempt.step_type == AttemptStepType.SWAP.value,
        )
        .first()
    )
    assert attempt is not None
    assert attempt.protocol == AttemptProtocol.INTERNAL_BUNDLE.value


def test_privy_external_deposit_does_not_create_intent(db: Session):
    pe = make_linked_client(db)
    deposit = _seed_confirmed_deposit(db, pe)
    db.commit()

    classification = classify_observed_external_privy_deposit(db, deposit)
    assert classification.get(OBSERVED_EXTERNAL_DEPOSIT_KEY) is True

    from services.onchain_indexer.models import TransactionIntent

    rows = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.product_type == IntentProductType.PRIVY_DEPOSIT.value,
        )
        .count()
    )
    assert rows == 0


def test_privy_deposit_not_required_in_attempt_gaps(db: Session):
    pe = make_linked_client(db)
    _seed_confirmed_deposit(db, pe)
    db.commit()

    gaps = scan_attempt_gaps_for_person(db, pe.person_id)
    privy_gaps = [g for g in gaps if "privy" in g.get("gap_type", "")]
    assert privy_gaps == []

    report = build_gap_report(db, person_id=pe.person_id)
    assert "privy_inbound_deposit" in " ".join(report.get("excluded_from_phase2", []))


def test_backfill_report_dry_run_structure(db: Session):
    report = build_backfill_report(db)
    assert report["ready"] is True
    assert report["dry_run"] is True
    summary = report["summary"]
    assert "attempts_to_create" in summary
    assert "legacy_records_covered" in summary
    assert "grouped_secondary_records" in summary
    assert "duplicate_tx_hash_groups_count" in summary
    assert summary["attempts_to_create"] <= summary["legacy_records_covered"]
    assert "attempt_candidates" in report


def test_service_mark_submitted_and_confirmed(db: Session):
    pe = make_linked_client(db)
    idem = f"svc-{uuid.uuid4().hex[:12]}"
    OnchainTransactionAttemptService.create_prepared_attempt(
        db,
        AttemptCreateInput(
            person_id=pe.person_id,
            chain_id=8453,
            protocol=AttemptProtocol.LIFI.value,
            operation_type="swap",
            step_type=AttemptStepType.SWAP.value,
            idempotency_key=idem,
        ),
    )
    tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    from services.transaction_attempts.schemas import AttemptTransitionInput

    submitted = OnchainTransactionAttemptService.mark_submitted(
        db,
        idempotency_key=idem,
        step_type=AttemptStepType.SWAP.value,
        transition=AttemptTransitionInput(tx_hash=tx),
    )
    confirmed = OnchainTransactionAttemptService.mark_confirmed(
        db,
        idempotency_key=idem,
        step_type=AttemptStepType.SWAP.value,
    )
    db.commit()

    assert submitted is not None
    assert submitted["status"] == "submitted"
    assert confirmed is not None
    assert confirmed["status"] == "confirmed"


def test_two_internal_bundle_swaps_same_tx_hash_one_attempt_candidate(db: Session):
    pe = make_linked_client(db)
    portfolio_id = str(uuid.uuid4())
    shared_tx = f"0xgroup-{uuid.uuid4().hex[:56]}"
    audit = [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": "batch-group-test",
            "bundle_action": "allocation",
        }
    ]
    swap_a = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="WETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("100"),
        estimated_receive=Decimal("0.04"),
        tx_hash=shared_tx,
        audit_log=audit,
    )
    swap_b = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("50"),
        estimated_receive=Decimal("49"),
        tx_hash=shared_tx,
        audit_log=audit,
    )
    db.add(swap_a)
    db.add(swap_b)
    db.flush()

    plan = build_backfill_plan(db, person_id=pe.person_id)
    swap_attempts = [
        a
        for a in plan["attempts"]
        if a["step_type"] == AttemptStepType.SWAP.value
        and a.get("tx_hash") == shared_tx.lower()
    ]
    assert len(swap_attempts) == 1
    candidate = swap_attempts[0]
    assert candidate["idempotency_key"] == tx_hash_backfill_idempotency_key(
        chain_id=8453, tx_hash=shared_tx
    )
    assert candidate["grouping"]["legacy_records_in_group"] == 2
    assert len(candidate["raw_submission_json"]["secondary_legacy_records"]) == 1
    secondary_ids = {
        r["reference_id"] for r in candidate["raw_submission_json"]["secondary_legacy_records"]
    }
    assert secondary_ids == {str(swap_a.id), str(swap_b.id)} - {candidate["reference_id"]}

    gaps = scan_attempt_gaps_for_person(db, pe.person_id)
    swap_missing = [g for g in gaps if g["gap_type"] == "swap_missing_swap_attempt"]
    grouped_info = [
        g for g in gaps if g["gap_type"] == "legacy_records_grouped_under_single_attempt"
    ]
    assert len(swap_missing) == 1
    assert swap_missing[0]["metadata"]["legacy_records_in_group"] == 2
    assert len(grouped_info) >= 1


def test_group_legacy_records_unique_chain_tx_keys():
    shared_tx = "0xabc123"
    records = [
        {
            "source": "person_wallet_swaps",
            "reference_id": "swap-1",
            "person_id": "p1",
            "chain_id": 8453,
            "tx_hash": shared_tx,
            "step_type": "swap",
            "protocol": "internal_bundle",
            "intent_id": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "amount_in": "10",
            "legacy_idempotency_key": "lifi:swap-1:swap",
        },
        {
            "source": "person_wallet_swaps",
            "reference_id": "swap-2",
            "person_id": "p1",
            "chain_id": 8453,
            "tx_hash": shared_tx,
            "step_type": "swap",
            "protocol": "internal_bundle",
            "intent_id": "intent-1",
            "created_at": "2026-01-02T00:00:00+00:00",
            "amount_in": "5",
            "legacy_idempotency_key": "lifi:swap-2:swap",
        },
    ]
    grouped, ungrouped, dupes = group_legacy_records_by_chain_tx(records)
    assert len(grouped) == 1
    assert len(ungrouped) == 0
    assert len(dupes) == 1
    assert grouped[0]["reference_id"] == "swap-2"
    assert grouped[0]["intent_id"] == "intent-1"
    assert grouped[0]["raw_submission_json"]["backfill_grouped_by_tx_hash"] is True
    assert len(grouped[0]["raw_submission_json"]["secondary_legacy_records"]) == 1
    assert grouped[0]["idempotency_key"] == tx_hash_backfill_idempotency_key(
        chain_id=8453, tx_hash=shared_tx
    )
