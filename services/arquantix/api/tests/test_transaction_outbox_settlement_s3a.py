"""Phase 2 S3a — worker outbox ``intent.settle`` → settlement skeleton NOOP."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.cost_basis.models import CostBasisExecution
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.result import SettlementOutcome, SettlementResult
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)
from services.transaction_outbox.settlement_worker import (
    handle_intent_settle_event,
    process_transaction_outbox_intent_settle,
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


def _economic_counts(db: Session, person_id) -> dict[str, int]:
    return {
        "balances": db.query(PersonWalletBalance)
        .filter(PersonWalletBalance.person_id == person_id)
        .count(),
        "deposits": db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == person_id)
        .count(),
        "pe_atoms": db.query(PositionAtom).count(),
        "bundle_ledger": db.query(BundleLedgerEntry).count(),
        "cost_basis": db.query(CostBasisExecution).count(),
    }


def _seed_queued_intent_settle_outbox(db: Session, monkeypatch=None):
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
        amount_in=Decimal("10"),
    )
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    settle_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
        payload_json={"s3a": True},
    )
    db.commit()
    return pe, bundle, settle_outbox


def test_s3a_settlement_worker_disabled_by_default(db: Session, monkeypatch):
    monkeypatch.delenv("LIFI_OUTBOX_WORKER_ENABLED", raising=False)
    result = process_transaction_outbox_intent_settle(db)
    assert result["skipped"] is True
    assert result["polled"] == 0


def test_s3a_intent_settle_success_persists_hash_and_processes_outbox(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    pe, bundle, settle_outbox = _seed_queued_intent_settle_outbox(db, monkeypatch)
    before = _economic_counts(db, pe.person_id)
    transitions_before = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )

    result = process_transaction_outbox_intent_settle(db)
    assert result["enabled"] is True
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(settle_outbox)
    meta = bundle.intent.metadata_json or {}
    assert meta.get(SETTLEMENT_RECEIPT_METADATA_KEY)
    assert len(str(meta[SETTLEMENT_RECEIPT_METADATA_KEY])) == 64
    assert bundle.intent.current_phase == IntentOrchestratorPhase.SETTLED_NOOP.value
    assert bundle.intent.status == IntentStatus.CREATED.value
    assert bundle.intent.status not in {"COMPLETED", "completed"}
    assert settle_outbox.status == OutboxEventStatus.PROCESSED.value

    transitions_after = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )
    assert transitions_after == transitions_before + 1
    assert _economic_counts(db, pe.person_id) == before


def test_s3a_second_passage_noop_already_settled_no_double_write(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    pe, bundle, first_outbox = _seed_queued_intent_settle_outbox(db, monkeypatch)
    before = _economic_counts(db, pe.person_id)

    first = process_transaction_outbox_intent_settle(db)
    assert first["processed"] == 1

    db.refresh(bundle.intent)
    first_hash = (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY)
    transitions_after_first = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )

    second_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
    )
    db.commit()

    second = process_transaction_outbox_intent_settle(db)
    assert second["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(second_outbox)
    assert (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY) == first_hash
    assert second_outbox.status == OutboxEventStatus.PROCESSED.value
    assert TransactionIntentTransitionRepository.count_for_intent(db, bundle.intent.id) == (
        transitions_after_first
    )
    assert _economic_counts(db, pe.person_id) == before


def test_s3a_retryable_failure_retries_outbox_without_new_hash(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    pe, bundle, settle_outbox = _seed_queued_intent_settle_outbox(db, monkeypatch)

    def _retryable(_db: Session, *, intent_id: UUID) -> SettlementResult:
        return SettlementResult(
            outcome=SettlementOutcome.RETRYABLE_FAILURE,
            intent_id=intent_id,
            error_code="test.retryable",
            error_message="simulated transient failure",
        )

    monkeypatch.setattr(
        "services.transaction_outbox.settlement_worker.settle_transaction_intent_idempotently",
        _retryable,
    )

    result = process_transaction_outbox_intent_settle(db)
    assert result["retried"] == 1
    assert result["processed"] == 0

    db.refresh(settle_outbox)
    db.refresh(bundle.intent)
    assert settle_outbox.status == OutboxEventStatus.PENDING.value
    assert settle_outbox.attempt_count == 1
    assert (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY) is None
    assert bundle.intent.current_phase == IntentOrchestratorPhase.QUEUED.value
    assert _economic_counts(db, pe.person_id) == _economic_counts(db, pe.person_id)


def test_s3a_terminal_failure_marks_intent_failed_and_processes_outbox(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    pe, bundle, settle_outbox = _seed_queued_intent_settle_outbox(db, monkeypatch)
    bundle.intent.idempotency_key = "   "
    db.commit()

    result = process_transaction_outbox_intent_settle(db)
    assert result["processed"] == 1

    db.refresh(bundle.intent)
    db.refresh(settle_outbox)
    assert bundle.intent.status == IntentStatus.FAILED.value
    assert settle_outbox.status == OutboxEventStatus.PROCESSED.value
    assert (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY) is None
    assert _economic_counts(db, pe.person_id) == _economic_counts(db, pe.person_id)


def test_s3a_handler_terminal_failure_transition_recorded(db: Session, monkeypatch):
    pe, bundle, settle_outbox = _seed_queued_intent_settle_outbox(db, monkeypatch)
    bundle.intent.idempotency_key = ""
    db.commit()
    transitions_before = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )

    handle_intent_settle_event(db, settle_outbox)
    TransactionOutboxRepository.mark_processed(db, settle_outbox)
    db.commit()

    db.refresh(bundle.intent)
    assert bundle.intent.status == IntentStatus.FAILED.value
    assert (
        TransactionIntentTransitionRepository.count_for_intent(db, bundle.intent.id)
        == transitions_before + 1
    )
    assert _economic_counts(db, pe.person_id) == _economic_counts(db, pe.person_id)
