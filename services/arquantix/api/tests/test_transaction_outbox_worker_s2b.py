"""Phase 2 S2b — worker outbox ``intent.created`` uniquement."""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.enums import OutboxEventStatus
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.models import TransactionIntentTransition, TransactionOutbox
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)
from services.transaction_outbox.worker import (
    handle_intent_created_event,
    process_transaction_outbox_intent_created,
)
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist


def _migration_173_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_outbox'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_173_ready(),
    reason="Migration 173 requise (transaction_outbox).",
)


def _economic_counts(db: Session, person_id) -> tuple[int, int]:
    balances = (
        db.query(PersonWalletBalance).filter(PersonWalletBalance.person_id == person_id).count()
    )
    deposits = (
        db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == person_id).count()
    )
    return balances, deposits


def _seed_pending_intent_created(db: Session, monkeypatch=None):
    pe = make_linked_client(db)
    if monkeypatch is not None:
        enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("25"),
    )
    db.commit()
    return pe, bundle


def test_s2b_worker_disabled_by_default(db: Session, monkeypatch):
    monkeypatch.delenv("LIFI_OUTBOX_WORKER_ENABLED", raising=False)
    result = process_transaction_outbox_intent_created(db)
    assert result["skipped"] is True
    assert result["polled"] == 0


def test_s2b_intent_created_transitions_and_marks_outbox_processed(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    pe, bundle = _seed_pending_intent_created(db, monkeypatch)
    bal_before, dep_before = _economic_counts(db, pe.person_id)
    transitions_before = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )

    result = process_transaction_outbox_intent_created(db)
    assert result["enabled"] is True
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(bundle.outbox)
    assert bundle.intent.current_phase == IntentOrchestratorPhase.QUEUED.value
    assert bundle.outbox.status == OutboxEventStatus.PROCESSED.value
    assert bundle.outbox.processed_at is not None

    transitions_after = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )
    assert transitions_after == transitions_before + 2

    bal_after, dep_after = _economic_counts(db, pe.person_id)
    assert bal_after == bal_before
    assert dep_after == dep_before


def test_s2b_handler_idempotent_when_already_queued(db: Session, monkeypatch):
    pe, bundle = _seed_pending_intent_created(db, monkeypatch)
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    db.commit()

    handle_intent_created_event(db, bundle.outbox)
    TransactionOutboxRepository.mark_processed(db, bundle.outbox)
    db.commit()

    count = TransactionIntentTransitionRepository.count_for_intent(db, bundle.intent.id)
    # bootstrap 1 + 0 new (already QUEUED)
    assert count == 1


def test_s2b_second_poll_no_double_process(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    _pe, bundle = _seed_pending_intent_created(db, monkeypatch)

    first = process_transaction_outbox_intent_created(db)
    assert first["processed"] == 1

    second = process_transaction_outbox_intent_created(db)
    assert second["processed"] == 0
    assert second["polled"] == 0

    transitions = (
        db.query(TransactionIntentTransition)
        .filter(TransactionIntentTransition.intent_id == bundle.intent.id)
        .count()
    )
    assert transitions == 3  # bootstrap + VALIDATED + QUEUED
