"""Tests Phase 2 — dual-write forward (nouvelles transactions, pas backfill)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.models import PersonWalletSwap
from services.transaction_attempts.dual_write import (
    dual_write_lifi_swap_confirmed,
    dual_write_vault_step,
)
from services.transaction_attempts.enums import AttemptProtocol, AttemptStepType
from services.transaction_attempts.models import OnchainTransactionAttempt
from services.transaction_attempts.repository import OnchainTransactionAttemptRepository
from services.transaction_intents.ledgity_intent_sync import (
    ensure_ledgity_intent_for_vault_transaction,
    mark_ledgity_intent_confirmed,
)
from services.transaction_intents.lifi_intent_sync import LINKED_TABLE, on_swap_created
from services.transaction_intents.lombard_intent_sync import (
    ensure_lombard_parent_intent,
    sync_lombard_step_from_ledger_receipt,
)
from services.transaction_intents.morpho_intent_sync import (
    mark_morpho_intent_confirmed,
    ensure_morpho_intent_for_vault_transaction,
    sync_morpho_vault_approve_attempt,
)
from services.transaction_intents.privy_deposit_intent_sync import (
    classify_observed_external_privy_deposit,
)
from services.transaction_attempts.reconciliation import migration_171_ready, scan_attempt_gaps_for_person
from services.transaction_attempts.tx_hash_canonical import tx_hash_canonical_idempotency_key
from services.transaction_intents.repository import TransactionIntentRepository
from tests.conftest import make_linked_client
from tests.test_phase1_transaction_intent_hardening import _seed_confirmed_deposit
from tests.test_phase4_reconciliation import _seed_wallet
from tests.test_phase7_transaction_intents import _migration_166_ready


def _migration_171_ready() -> bool:
    return migration_171_ready()


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_171_ready(), reason="Migration 171 requise."),
]


def _unique_tx(prefix: str = "fwd") -> str:
    return f"0x{prefix}{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"


def _forward_attempts_for_person(
    db: Session,
    person_id: uuid.UUID,
    *,
    since_count: int = 0,
) -> list[OnchainTransactionAttempt]:
    rows = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.person_id == person_id)
        .order_by(OnchainTransactionAttempt.created_at.desc())
        .all()
    )
    forward = [
        r
        for r in rows
        if isinstance(r.metadata_json, dict)
        and r.metadata_json.get("dual_write_source")
        and not r.metadata_json.get("backfill")
    ]
    return forward[since_count:] if since_count else forward


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


def _insert_morpho_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: uuid.UUID,
    wallet_address: str,
    vault_address: str,
    operation: str,
    group_key: str,
    tx_hash: str | None,
    status: str,
    tx_index: int = 0,
) -> None:
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status, tx_hash,
                idempotency_key, group_key, integration_mode, tx_index, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                :operation, '0', 'USDC', 6, :status, :tx_hash,
                :group_key, :group_key, 'direct_morpho', :tx_index, NOW(), NOW()
            )
            """
        ),
        {
            "id": ovt_id,
            "person_id": str(person_id),
            "vault": vault_address.lower(),
            "wallet": wallet_address.lower(),
            "operation": operation,
            "status": status,
            "tx_hash": tx_hash,
            "group_key": group_key,
            "tx_index": tx_index,
        },
    )


def _attempt_report(row: OnchainTransactionAttempt) -> dict[str, Any]:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "id": str(row.id),
        "protocol": row.protocol,
        "step_type": row.step_type,
        "status": row.status,
        "tx_hash": row.tx_hash,
        "intent_id": str(row.intent_id) if row.intent_id else None,
        "group_key": row.group_key,
        "linked_table": row.linked_table,
        "linked_id": str(row.linked_id) if row.linked_id else None,
        "linked_reference_id": row.linked_reference_id,
        "dual_write_source": meta.get("dual_write_source"),
    }


def test_forward_lifi_portal_approval_and_swap(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    before = len(_forward_attempts_for_person(db, pe.person_id))

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("25"),
        estimated_receive=Decimal("24"),
        audit_log=[{"event": "awaiting_signature"}],
    )
    db.add(swap)
    db.flush()
    on_swap_created(db, swap)
    db.flush()

    svc = LifiExecuteService()
    approval_tx = _unique_tx("appr")
    swap_tx = _unique_tx("swap")

    svc.record_token_approval(
        db,
        person_id=pe.person_id,
        swap_id=swap.id,
        tx_hash=approval_tx,
    )
    db.flush()

    from services.transaction_intents.lifi_intent_sync import on_swap_submitted

    swap.status = SwapSessionStatus.SUBMITTED.value
    swap.tx_hash = swap_tx
    on_swap_submitted(db, swap, tx_hash=swap_tx)
    from services.transaction_attempts.dual_write import dual_write_lifi_swap_submitted

    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap_tx)
    dual_write_lifi_swap_confirmed(db, swap, tx_hash=swap_tx)
    db.commit()
    db.refresh(swap)

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent is not None

    created = _forward_attempts_for_person(db, pe.person_id, since_count=before)
    assert len(created) == 2
    approve = next(a for a in created if a.step_type == AttemptStepType.APPROVE.value)
    swap_attempt = next(a for a in created if a.step_type == AttemptStepType.SWAP.value)

    assert approve.protocol == AttemptProtocol.LIFI.value
    assert swap_attempt.protocol == AttemptProtocol.LIFI.value
    assert approve.status == "submitted"
    assert swap_attempt.status == "confirmed"
    assert str(approve.intent_id) == str(intent.id)
    assert str(swap_attempt.intent_id) == str(intent.id)
    assert approve.tx_hash == approval_tx.lower()
    assert swap_attempt.tx_hash == swap_tx.lower()
    assert approve.tx_hash != swap_attempt.tx_hash
    assert swap_attempt.linked_table == "person_wallet_swaps"
    assert str(swap_attempt.linked_id) == str(swap.id)
    assert swap.status in {SwapSessionStatus.SUBMITTED.value, SwapSessionStatus.CONFIRMED.value}


def test_forward_lifi_submit_signed_tx_path(db: Session):
    """Chemin submit_signed_tx réel (hors mock) déclenche dual_write swap submitted."""
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
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
    swap_tx = _unique_tx("exec")
    svc = LifiExecuteService()
    with patch("services.lifi.lifi_execute_service.swaps_mock_mode", return_value=False):
        with patch.object(LifiExecuteService, "refresh_lifi_status", return_value=None):
            svc.submit_signed_tx(
                db,
                person_id=pe.person_id,
                swap_id=swap.id,
                tx_hash=swap_tx,
            )
    db.commit()
    attempt = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == swap_tx.lower(),
            OnchainTransactionAttempt.step_type == AttemptStepType.SWAP.value,
        )
        .first()
    )
    assert attempt is not None
    assert attempt.status == "submitted"
    assert attempt.idempotency_key == tx_hash_canonical_idempotency_key(
        chain_id=8453, tx_hash=swap_tx
    )


def test_forward_bundle_internal_swap(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    before = len(_forward_attempts_for_person(db, pe.person_id))
    portfolio_id = str(uuid.uuid4())
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    tx = _unique_tx("bundle")

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="WETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("100"),
        estimated_receive=Decimal("0.04"),
        audit_log=[
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "portfolio_id": portfolio_id,
                "batch_id": batch_id,
                "bundle_action": "allocation",
            }
        ],
    )
    db.add(swap)
    db.flush()
    on_swap_created(db, swap)

    from services.transaction_intents.lifi_intent_sync import on_swap_submitted
    from services.transaction_attempts.dual_write import dual_write_lifi_swap_submitted

    swap.status = SwapSessionStatus.SUBMITTED.value
    swap.tx_hash = tx
    on_swap_submitted(db, swap, tx_hash=tx)
    dual_write_lifi_swap_submitted(db, swap, tx_hash=tx)
    dual_write_lifi_swap_confirmed(db, swap, tx_hash=tx)
    db.commit()

    created = _forward_attempts_for_person(db, pe.person_id, since_count=before)
    assert len(created) == 1
    attempt = created[0]
    assert attempt.protocol == AttemptProtocol.INTERNAL_BUNDLE.value
    assert attempt.step_type == AttemptStepType.SWAP.value
    assert attempt.tx_hash == tx.lower()
    assert attempt.group_key == str(swap.id)
    assert attempt.linked_table == "person_wallet_swaps"

    dupes = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == attempt.chain_id,
            OnchainTransactionAttempt.tx_hash == attempt.tx_hash,
        )
        .count()
    )
    assert dupes == 1
    assert attempt.idempotency_key == tx_hash_canonical_idempotency_key(chain_id=8453, tx_hash=tx)


def test_forward_two_bundle_swaps_same_tx_hash_single_attempt(db: Session):
    pe = make_linked_client(db)
    portfolio_id = str(uuid.uuid4())
    shared_tx = _unique_tx("bundle2")
    audit = [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": "batch-shared",
            "bundle_action": "allocation",
        }
    ]
    swap_a = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="WETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("50"),
        estimated_receive=Decimal("0.02"),
        tx_hash=shared_tx,
        audit_log=audit,
    )
    swap_b = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("30"),
        estimated_receive=Decimal("29"),
        tx_hash=shared_tx,
        audit_log=audit,
    )
    db.add(swap_a)
    db.add(swap_b)
    db.flush()

    from services.transaction_attempts.dual_write import (
        dual_write_lifi_swap_submitted,
        dual_write_lifi_swap_confirmed,
    )

    dual_write_lifi_swap_submitted(db, swap_a, tx_hash=shared_tx)
    dual_write_lifi_swap_submitted(db, swap_b, tx_hash=shared_tx)
    dual_write_lifi_swap_confirmed(db, swap_a, tx_hash=shared_tx)
    dual_write_lifi_swap_confirmed(db, swap_b, tx_hash=shared_tx)
    db.commit()

    attempts = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == shared_tx.lower(),
            OnchainTransactionAttempt.step_type == AttemptStepType.SWAP.value,
        )
        .all()
    )
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.protocol == AttemptProtocol.INTERNAL_BUNDLE.value
    assert str(attempt.linked_id) == str(swap_a.id)
    meta = attempt.metadata_json if isinstance(attempt.metadata_json, dict) else {}
    secondaries = meta.get("secondary_legacy_records") or []
    assert meta.get("grouped_by_tx_hash") is True
    assert len(secondaries) == 1
    assert secondaries[0]["reference_id"] == str(swap_b.id)

    gaps = scan_attempt_gaps_for_person(db, pe.person_id)
    swap_missing = [g for g in gaps if g["gap_type"] == "swap_missing_swap_attempt"]
    assert swap_missing == []


def test_forward_same_swap_replay_idempotent(db: Session):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("9"),
        tx_hash=_unique_tx("replay"),
        audit_log=[],
    )
    db.add(swap)
    db.flush()

    from services.transaction_attempts.dual_write import dual_write_lifi_swap_submitted

    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap.tx_hash)
    dual_write_lifi_swap_submitted(db, swap, tx_hash=swap.tx_hash)
    db.commit()

    count = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == swap.tx_hash.lower(),
        )
        .count()
    )
    assert count == 1


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_forward_morpho_vault_approve_and_deposit(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    before = len(_forward_attempts_for_person(db, pe.person_id))
    group_key = f"morpho-fwd-{uuid.uuid4().hex[:10]}"
    approve_ovt = f"cl{uuid.uuid4().hex[:22]}"
    deposit_ovt = f"cl{uuid.uuid4().hex[:22]}"
    tx_approve = _unique_tx("mappr")
    tx_deposit = _unique_tx("mdep")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    _insert_morpho_ovt(
        db,
        ovt_id=approve_ovt,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="approve",
        group_key=group_key,
        tx_hash=tx_approve,
        status="success",
        tx_index=0,
    )
    _insert_morpho_ovt(
        db,
        ovt_id=deposit_ovt,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="deposit",
        group_key=group_key,
        tx_hash=tx_deposit,
        status="success",
        tx_index=1,
    )

    approve_result = sync_morpho_vault_approve_attempt(
        db,
        person_id=pe.person_id,
        vault_transaction_id=approve_ovt,
        tx_hash=tx_approve,
        vault_status="success",
    )
    ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=group_key,
        tx_index=1,
        tx_hash=tx_deposit,
        vault_status="success",
    )
    mark_morpho_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        tx_hash=tx_deposit,
    )
    db.commit()

    assert approve_result is not None
    assert approve_result["intent_id"] is None
    assert TransactionIntentRepository.find_by_vault_transaction(db, vault_transaction_id=approve_ovt) is None

    created = _forward_attempts_for_person(db, pe.person_id, since_count=before)
    assert len(created) == 2
    approve = next(a for a in created if a.step_type == AttemptStepType.APPROVE.value)
    deposit = next(a for a in created if a.step_type == AttemptStepType.DEPOSIT.value)

    assert approve.protocol == AttemptProtocol.MORPHO.value
    assert deposit.protocol == AttemptProtocol.MORPHO.value
    assert approve.group_key == group_key
    assert deposit.group_key == group_key
    assert approve.linked_reference_id == approve_ovt
    assert deposit.linked_reference_id == deposit_ovt
    assert deposit.intent_id is not None
    assert approve.intent_id is None
    assert approve.tx_hash != deposit.tx_hash
    assert (approve.metadata_json or {}).get("dual_write_source") == "morpho_vault_approve_sync"

    gaps = scan_attempt_gaps_for_person(db, pe.person_id)
    missing = [
        g for g in gaps
        if g.get("gap_type") == "vault_tx_missing_attempt"
        and g.get("reference_id") in {approve_ovt, deposit_ovt}
    ]
    assert missing == []


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_forward_morpho_vault_approve_sync_idempotent(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    group_key = f"morpho-idem-{uuid.uuid4().hex[:10]}"
    approve_ovt = f"cl{uuid.uuid4().hex[:22]}"
    tx_approve = _unique_tx("midem")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    _insert_morpho_ovt(
        db,
        ovt_id=approve_ovt,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="approve",
        group_key=group_key,
        tx_hash=tx_approve,
        status="success",
    )

    sync_morpho_vault_approve_attempt(
        db,
        person_id=pe.person_id,
        vault_transaction_id=approve_ovt,
        tx_hash=tx_approve,
        vault_status="success",
    )
    sync_morpho_vault_approve_attempt(
        db,
        person_id=pe.person_id,
        vault_transaction_id=approve_ovt,
        tx_hash=tx_approve,
        vault_status="success",
    )
    db.commit()

    count = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.linked_reference_id == approve_ovt,
            OnchainTransactionAttempt.step_type == AttemptStepType.APPROVE.value,
        )
        .count()
    )
    assert count == 1
    assert (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == 8453,
            OnchainTransactionAttempt.tx_hash == tx_approve.lower(),
        )
        .count()
    ) == 1


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_forward_morpho_vault_deposit_pending_then_receipt_confirms_attempt(db: Session):
    """Repro prod: prepared au pending, confirmed au receipt (même attempt)."""
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    group_key = f"morpho-rcpt-{uuid.uuid4().hex[:10]}"
    deposit_ovt = f"cl{uuid.uuid4().hex[:22]}"
    tx_deposit = _unique_tx("mrcpt")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    _insert_morpho_ovt(
        db,
        ovt_id=deposit_ovt,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="deposit",
        group_key=group_key,
        tx_hash=None,
        status="pending",
        tx_index=1,
    )

    ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=group_key,
        tx_index=1,
        vault_status="pending",
    )
    db.flush()

    prepared = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.linked_reference_id == deposit_ovt)
        .one()
    )
    assert prepared.status == "prepared"
    assert prepared.tx_hash is None

    mark_morpho_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        tx_hash=tx_deposit,
    )
    mark_morpho_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        tx_hash=tx_deposit,
    )
    db.commit()

    attempts = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.linked_reference_id == deposit_ovt)
        .all()
    )
    assert len(attempts) == 1
    att = attempts[0]
    assert att.status == "confirmed"
    assert att.tx_hash == tx_deposit.lower()
    assert att.linked_reference_id == deposit_ovt
    assert att.intent_id is not None

    trace_confirmed = db.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM transaction_trace_events
            WHERE attempt_id = :aid
              AND event_type = 'attempt_confirmed'
            """
        ),
        {"aid": att.id},
    ).scalar()
    assert trace_confirmed >= 1

    gaps = scan_attempt_gaps_for_person(db, pe.person_id)
    stale = [
        g
        for g in gaps
        if g.get("reference_id") == deposit_ovt
        and g.get("gap_type") in (
            "vault_tx_missing_attempt",
            "vault_attempt_inconsistent_with_legacy",
        )
    ]
    assert stale == []


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_forward_ledgity_vault_deposit_pending_then_receipt_confirms_attempt(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    group_key = f"ledgity-rcpt-{uuid.uuid4().hex[:10]}"
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    tx = _unique_tx("lrcpt")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    _insert_morpho_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="deposit",
        group_key=group_key,
        tx_hash=None,
        status="pending",
        tx_index=0,
    )
    db.execute(
        sa.text(
            "UPDATE onchain_vault_transactions SET integration_mode = 'ledgity_vault' WHERE id = :id"
        ),
        {"id": ovt_id},
    )

    ensure_ledgity_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=ovt_id,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=group_key,
        tx_index=0,
        vault_status="pending",
    )
    db.flush()

    prepared = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.linked_reference_id == ovt_id)
        .one()
    )
    assert prepared.status == "prepared"
    assert prepared.protocol == AttemptProtocol.LEDGITY.value

    mark_ledgity_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=ovt_id,
        tx_hash=tx,
    )
    db.commit()

    att = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.linked_reference_id == ovt_id)
        .one()
    )
    assert att.status == "confirmed"
    assert att.tx_hash == tx.lower()


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_gap_report_detects_stale_vault_attempt_then_clears_after_receipt(db: Session):
    """OVT success + attempt prepared → gap ; receipt → gap disparu."""
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    group_key = f"morpho-gap-{uuid.uuid4().hex[:10]}"
    deposit_ovt = f"cl{uuid.uuid4().hex[:22]}"
    tx_deposit = _unique_tx("mgap")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    _insert_morpho_ovt(
        db,
        ovt_id=deposit_ovt,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        vault_address=vault,
        operation="deposit",
        group_key=group_key,
        tx_hash=None,
        status="pending",
        tx_index=1,
    )
    ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=group_key,
        tx_index=1,
        vault_status="pending",
    )
    db.execute(
        sa.text(
            """
            UPDATE onchain_vault_transactions
            SET status = 'success', tx_hash = :tx
            WHERE id = :id
            """
        ),
        {"id": deposit_ovt, "tx": tx_deposit},
    )
    db.flush()

    gaps_before = scan_attempt_gaps_for_person(db, pe.person_id)
    inconsistent = [
        g
        for g in gaps_before
        if g.get("gap_type") == "vault_attempt_inconsistent_with_legacy"
        and g.get("reference_id") == deposit_ovt
    ]
    assert len(inconsistent) == 1

    mark_morpho_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=deposit_ovt,
        tx_hash=tx_deposit,
    )
    db.commit()

    gaps_after = scan_attempt_gaps_for_person(db, pe.person_id)
    assert [
        g
        for g in gaps_after
        if g.get("reference_id") == deposit_ovt
        and g.get("gap_type") == "vault_attempt_inconsistent_with_legacy"
    ] == []


def test_forward_ledgity_vault_deposit_lifecycle(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    before = len(_forward_attempts_for_person(db, pe.person_id))
    group_key = f"ledgity-fwd-{uuid.uuid4().hex[:8]}"
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    tx = _unique_tx("ldep")
    vault = f"0x{uuid.uuid4().hex[:40]}"

    ensure_ledgity_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=ovt_id,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=group_key,
        tx_index=0,
        tx_hash=tx,
        vault_status="success",
    )
    mark_ledgity_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=ovt_id,
        tx_hash=tx,
    )
    db.commit()

    created = _forward_attempts_for_person(db, pe.person_id, since_count=before)
    assert len(created) == 1
    attempt = created[0]
    assert attempt.protocol == AttemptProtocol.LEDGITY.value
    assert attempt.step_type == AttemptStepType.DEPOSIT.value
    assert attempt.status == "confirmed"
    assert attempt.group_key == group_key
    assert attempt.linked_reference_id == ovt_id
    assert attempt.intent_id is not None


def test_forward_lombard_borrow_ordered_steps(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    before = len(_forward_attempts_for_person(db, pe.person_id))
    market = f"0xmarket{uuid.uuid4().hex[:32]}"
    gk = f"lombard-fwd-{uuid.uuid4().hex[:12]}"
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

    for lid in ledger_ids:
        sync_lombard_step_from_ledger_receipt(
            db,
            person_id=pe.person_id,
            group_key=gk,
            market_or_vault=market,
            ledger_entry_id=lid,
            tx_hash=_unique_tx("lom"),
            ledger_status="success",
        )
    db.commit()

    parent = TransactionIntentRepository.find_by_lombard_group(
        db, person_id=pe.person_id, group_key=gk, market_or_vault=market
    )
    assert parent is not None

    created = _forward_attempts_for_person(db, pe.person_id, since_count=before)
    assert len(created) == 3
    assert [a.step_type for a in sorted(created, key=lambda x: x.step_index)] == [
        AttemptStepType.APPROVE.value,
        AttemptStepType.AUTHORIZE.value,
        AttemptStepType.OPEN_LOAN.value,
    ]
    assert all(a.group_key == gk for a in created)
    assert all(a.protocol == AttemptProtocol.LOMBARD.value for a in created)
    assert all(str(a.intent_id) == str(parent.id) for a in created if a.intent_id)


def test_forward_privy_external_deposit_no_attempt(db: Session):
    pe = make_linked_client(db)
    before_privy = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.protocol == AttemptProtocol.PRIVY.value)
        .count()
    )
    deposit = _seed_confirmed_deposit(db, pe)
    classify_observed_external_privy_deposit(db, deposit)
    db.commit()

    after_privy = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.protocol == AttemptProtocol.PRIVY.value)
        .count()
    )
    assert after_privy == before_privy == 0

    from services.onchain_indexer.models import TransactionIntent
    from services.transaction_intents.enums import IntentProductType

    assert (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.product_type == IntentProductType.PRIVY_DEPOSIT.value,
        )
        .count()
        == 0
    )
