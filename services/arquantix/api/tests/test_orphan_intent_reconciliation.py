"""PR 1 — réconciliation read/repair-only des intents orchestrateur orphelins.

Couvre la matrice : swap terminal -> intent terminal (T8), pas d'orphelin (T6),
idempotence, no-op si non terminal, hook worker bookkeeping, visibilité.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentStatus
from services.transaction_intents.orphan_intent_reconciliation import (
    find_orphaned_lifi_intents,
    reconcile_intent_from_linked_swap,
    reconcile_orphaned_lifi_intents,
)
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.repository import TransactionOutboxRepository
from services.transaction_outbox.worker import handle_intent_created_event
from tests.conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def _migration_outbox_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' AND indexname = 'uq_outbox_intent_event_type'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_outbox_ready(),
    reason="Migration 174 (uq_outbox_intent_event_type) requise.",
)


def _seed_orchestrator_swap(
    db: Session,
    *,
    swap_status: str,
    to_asset: str = "CBBTC",
):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=swap_status,
        from_asset="USDC",
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("2"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc),
        estimated_receive=Decimal("0.00003"),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()
    attach_orchestrator_intent_to_swap_atomic(db, person_id=pe.person_id, swap_id=swap.id)
    intent = db.query(TransactionIntent).filter(TransactionIntent.linked_id == swap.id).one()
    db.commit()
    db.refresh(swap)
    db.refresh(intent)
    return pe, swap, intent


def _age_intent(db: Session, intent: TransactionIntent, minutes: int = 30) -> None:
    intent.updated_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    db.commit()
    db.refresh(intent)


def test_failed_swap_reconciles_intent_to_failed(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    assert intent.status == IntentStatus.CREATED.value

    result = reconcile_intent_from_linked_swap(db, intent)
    db.commit()
    db.refresh(intent)

    assert result.action == "repaired"
    assert result.to_status == IntentStatus.FAILED.value
    assert result.reason == "linked_swap_terminal_failed"
    assert intent.status == IntentStatus.FAILED.value


def test_expired_swap_reconciles_intent_to_failed(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.EXPIRED.value)
    result = reconcile_intent_from_linked_swap(db, intent)
    db.commit()
    db.refresh(intent)
    assert result.action == "repaired"
    assert intent.status == IntentStatus.FAILED.value


def test_records_transition(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    reconcile_intent_from_linked_swap(db, intent)
    db.commit()
    rows = db.execute(
        sa.text(
            "SELECT actor, from_status, to_status FROM transaction_intent_transitions "
            "WHERE intent_id = :iid AND actor = 'intent_swap_reconciler'"
        ),
        {"iid": str(intent.id)},
    ).mappings().all()
    assert len(rows) == 1
    assert rows[0]["to_status"] == IntentStatus.FAILED.value
    assert rows[0]["from_status"] == IntentStatus.CREATED.value


def test_non_terminal_swap_is_noop(db: Session):
    _, swap, intent = _seed_orchestrator_swap(
        db, swap_status=SwapSessionStatus.QUOTE_RECEIVED.value
    )
    result = reconcile_intent_from_linked_swap(db, intent)
    assert result.action == "noop"
    assert result.reason.startswith("swap_not_terminal")
    assert intent.status == IntentStatus.CREATED.value


def test_confirmed_without_settlement_is_noop(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.CONFIRMED.value)
    result = reconcile_intent_from_linked_swap(db, intent)
    assert result.action == "noop"
    assert result.reason == "swap_confirmed_pending_settlement"
    assert intent.status == IntentStatus.CREATED.value


def test_idempotent_when_already_terminal(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    reconcile_intent_from_linked_swap(db, intent)
    db.commit()
    second = reconcile_intent_from_linked_swap(db, intent)
    assert second.action == "noop"
    assert second.reason == "intent_already_terminal"


def test_dry_run_does_not_mutate(db: Session):
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    result = reconcile_intent_from_linked_swap(db, intent, dry_run=True)
    assert result.action == "repaired"
    assert result.to_status == IntentStatus.FAILED.value
    db.refresh(intent)
    assert intent.status == IntentStatus.CREATED.value


def test_find_orphaned_lists_failed_swap_intent(db: Session):
    pe, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    _age_intent(db, intent, minutes=30)

    items = find_orphaned_lifi_intents(db, older_than_minutes=10, person_id=pe.person_id)
    ids = {i["intent_id"] for i in items}
    assert str(intent.id) in ids
    match = next(i for i in items if i["intent_id"] == str(intent.id))
    assert match["would_set_status"] == IntentStatus.FAILED.value


def test_reconcile_batch_repairs(db: Session):
    pe, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    _age_intent(db, intent, minutes=30)

    report = reconcile_orphaned_lifi_intents(
        db, dry_run=False, older_than_minutes=10, person_id=pe.person_id
    )
    assert report["repaired"] >= 1
    db.refresh(intent)
    assert intent.status == IntentStatus.FAILED.value


def test_worker_hook_prevents_orphan(db: Session):
    """handle_intent_created_event réconcilie un swap déjà FAILED → intent failed."""
    _, swap, intent = _seed_orchestrator_swap(db, swap_status=SwapSessionStatus.FAILED.value)
    outbox = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_CREATED.value
    )[0]

    handle_intent_created_event(db, outbox)
    db.commit()
    db.refresh(intent)

    assert intent.status == IntentStatus.FAILED.value
