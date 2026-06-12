"""Incrément 4 — enqueue ``intent.execute`` + worker d'exécution serveur (flag OFF par défaut)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.execution_worker import (
    handle_intent_execute_event,
    process_transaction_outbox_intent_execute,
)
from services.transaction_outbox.orchestrator_execute_enqueue import (
    ENQUEUE_SOURCE,
    maybe_enqueue_orchestrator_intent_execute,
)
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_swap_routes import _seed_wallet

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


@dataclass
class _FakeResult:
    phase: str
    signed_server_side: bool
    fallback_reason: str | None = None


def _enable_execution_worker(monkeypatch, pe) -> None:
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")


def _seed_orchestrator_quoted_swap(
    db: Session,
    monkeypatch,
    *,
    status: str = SwapSessionStatus.QUOTE_RECEIVED.value,
    enable_worker: bool = True,
):
    pe = make_linked_client(db)
    if enable_worker:
        _enable_execution_worker(monkeypatch, pe)
    else:
        enable_lifi_orchestrator_allowlist(monkeypatch, pe)
        monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _seed_wallet(db, pe)

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
        from_asset="USDC",
        to_asset="AAVE",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc),
        estimated_receive=Decimal("0.05"),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()

    attach_orchestrator_intent_to_swap_atomic(db, person_id=pe.person_id, swap_id=swap.id)
    intent = db.query(TransactionIntent).filter(TransactionIntent.linked_id == swap.id).one()
    intent.current_phase = "QUEUED"
    db.commit()
    db.refresh(swap)
    db.refresh(intent)
    return pe, swap, intent


def _execute_count(db: Session, intent_id) -> int:
    return len(
        TransactionOutboxRepository.find_by_intent(
            db, intent_id, event_type=OutboxEventType.INTENT_EXECUTE.value
        )
    )


def test_quoted_swap_enqueues_one_intent_execute(db: Session, monkeypatch):
    pe, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch)

    result = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()

    assert result.enqueued is True
    assert result.outbox is not None
    assert result.outbox.event_type == OutboxEventType.INTENT_EXECUTE.value
    assert (result.outbox.payload_json or {}).get("source") == ENQUEUE_SOURCE
    assert (result.outbox.payload_json or {}).get("swap_id") == str(swap.id)
    assert _execute_count(db, intent.id) == 1


def test_rerun_no_duplicate_intent_execute(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch)

    first = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()
    second = maybe_enqueue_orchestrator_intent_execute(db, swap)

    assert first.enqueued is True
    assert second.enqueued is False
    assert second.reason == "intent_execute_already_enqueued"
    assert _execute_count(db, intent.id) == 1


def test_worker_disabled_no_enqueue(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch, enable_worker=False)

    result = maybe_enqueue_orchestrator_intent_execute(db, swap)
    assert result.enqueued is False
    assert result.reason == "execution_worker_not_enabled"
    assert _execute_count(db, intent.id) == 0


@pytest.mark.parametrize(
    "status",
    [
        SwapSessionStatus.CONFIRMED.value,
        SwapSessionStatus.SUBMITTED.value,
        SwapSessionStatus.FAILED.value,
    ],
)
def test_non_executable_status_no_enqueue(db: Session, monkeypatch, status: str):
    _, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch, status=status)

    result = maybe_enqueue_orchestrator_intent_execute(db, swap)
    assert result.enqueued is False
    assert result.reason.startswith("swap_status:")
    assert _execute_count(db, intent.id) == 0


def test_awaiting_signature_status_is_executable(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_quoted_swap(
        db, monkeypatch, status=SwapSessionStatus.AWAITING_SIGNATURE.value
    )

    result = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()
    assert result.enqueued is True
    assert _execute_count(db, intent.id) == 1


def test_handle_intent_execute_invokes_execute_fn(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch)
    enqueue = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()
    outbox = enqueue.outbox

    calls: list[tuple[UUID, UUID]] = []

    def _fake_execute(db_arg, *, person_id, swap_id):
        calls.append((person_id, swap_id))
        return _FakeResult(phase="confirmed", signed_server_side=True)

    summary = handle_intent_execute_event(db, outbox, execute_fn=_fake_execute)

    assert calls == [(swap.person_id, swap.id)]
    assert summary["signed_server_side"] is True
    assert summary["phase"] == "confirmed"


def test_handle_intent_execute_deferred_fallback(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_quoted_swap(db, monkeypatch)
    enqueue = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()

    def _fake_execute(db_arg, *, person_id, swap_id):
        return _FakeResult(
            phase="awaiting_signature",
            signed_server_side=False,
            fallback_reason="wallet_not_delegated",
        )

    summary = handle_intent_execute_event(db, enqueue.outbox, execute_fn=_fake_execute)
    assert summary["signed_server_side"] is False
    assert summary["fallback_reason"] == "wallet_not_delegated"


def test_process_intent_execute_disabled_skips(db: Session, monkeypatch):
    monkeypatch.delenv("LIFI_EXECUTION_WORKER_ENABLED", raising=False)
    result = process_transaction_outbox_intent_execute(db, limit=5)
    assert result["enabled"] is False
    assert result["skipped"] is True
