"""PR3 — enqueue-and-wait : 1 transaction active par user, le 2e swap attend (pas de 409).

Vérifie : (1) la logique du helper d'éligibilité, (2) le worker diffère (PENDING) un 2e
intent quand le slot user est déjà détenu, (3) le worker exécute quand le slot est libre,
(4) le confirm n'émet plus de 409 fail-fast pour des swaps concurrents en mode enqueue-and-wait.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.orchestrator_allowlist import lifi_enqueue_and_wait_enabled_for_person
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.financial_transaction_global_lock import (
    acquire_financial_transaction_global_lock_or_raise,
)
from services.product_locks.global_user_transaction_lock import (
    find_active_global_user_transaction_lock,
)
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.execution_worker import (
    process_transaction_outbox_intent_execute,
)
from services.transaction_outbox.orchestrator_execute_enqueue import (
    maybe_enqueue_orchestrator_intent_execute,
)
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_swap_routes import _auth_headers, _mock_lifi_quote, _seed_wallet

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
    swap_id: object
    phase: str
    signed_server_side: bool
    settled: bool = False
    tx_hash: str | None = None
    fallback_reason: str | None = None


def _enable_enqueue_and_wait(monkeypatch, pe) -> None:
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("LIFI_ENQUEUE_AND_WAIT_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")


def _seed_quoted_swap(db: Session, pe, *, to_asset: str = "AAVE") -> tuple[PersonWalletSwap, TransactionIntent]:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset=to_asset,
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
    return swap, intent


# --------------------------------------------------------------- helper logic


def test_helper_false_when_enqueue_flag_off(db: Session, monkeypatch):
    pe = make_linked_client(db, email="eaw-off@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    monkeypatch.setenv("LIFI_ENQUEUE_AND_WAIT_ENABLED", "false")
    assert lifi_enqueue_and_wait_enabled_for_person(db, pe.person_id) is False


def test_helper_false_when_authoritative_off(db: Session, monkeypatch):
    pe = make_linked_client(db, email="eaw-noauth@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "false")
    assert lifi_enqueue_and_wait_enabled_for_person(db, pe.person_id) is False


def test_helper_true_when_all_on(db: Session, monkeypatch):
    pe = make_linked_client(db, email="eaw-on@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    assert lifi_enqueue_and_wait_enabled_for_person(db, pe.person_id) is True


# --------------------------------------------------------------- worker defer / run


def test_worker_defers_second_intent_when_slot_held(db: Session, monkeypatch):
    """Le slot user est détenu par un autre intent → le 2e reste PENDING (enqueue-and-wait)."""
    pe = make_linked_client(db, email="eaw-defer@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    _seed_wallet(db, pe)

    # Intent A détient le slot global (swap "actif")
    _swap_a, intent_a = _seed_quoted_swap(db, pe, to_asset="AAVE")
    acquire_financial_transaction_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_a.id, reason="lifi_swap"
    )
    db.commit()

    # Intent B : event intent.execute en attente
    swap_b, intent_b = _seed_quoted_swap(db, pe, to_asset="ETH")
    enq = maybe_enqueue_orchestrator_intent_execute(db, swap_b)
    db.commit()
    assert enq.enqueued is True
    event_b = enq.outbox

    def _must_not_run(*a, **k):  # pragma: no cover - garde-fou
        raise AssertionError("execute ne doit pas tourner quand l'intent est différé")

    monkeypatch.setattr(
        "services.trade_core.server_execution.execute_prepared_swap_server_side", _must_not_run
    )

    result = process_transaction_outbox_intent_execute(db, limit=10)

    assert result["deferred"] == 1
    assert result["processed"] == 0
    db.refresh(event_b)
    assert event_b.status == OutboxEventStatus.PENDING.value


def test_worker_executes_when_slot_free(db: Session, monkeypatch):
    """Slot libre → le worker acquiert le slot pour l'intent et exécute."""
    pe = make_linked_client(db, email="eaw-run@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    _seed_wallet(db, pe)

    swap, intent = _seed_quoted_swap(db, pe, to_asset="AAVE")
    enq = maybe_enqueue_orchestrator_intent_execute(db, swap)
    db.commit()
    event = enq.outbox

    def _fake_execute(db_arg, *, person_id, swap_id):
        return _FakeResult(swap_id=swap_id, phase="confirmed", signed_server_side=True)

    monkeypatch.setattr(
        "services.trade_core.server_execution.execute_prepared_swap_server_side", _fake_execute
    )

    result = process_transaction_outbox_intent_execute(db, limit=10)

    assert result["processed"] == 1
    assert result["deferred"] == 0
    db.refresh(event)
    assert event.status == OutboxEventStatus.PROCESSED.value
    # Le worker a acquis le slot global pour CET intent.
    lock = find_active_global_user_transaction_lock(db, person_id=pe.person_id)
    assert lock is not None
    assert lock.intent_id == intent.id


# --------------------------------------------------------------- confirm: no 409 concurrent


def _post_quote(client: TestClient, db: Session, pe) -> dict:
    from services.lifi.routes import _quote_svc

    mock_client = MagicMock()
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1",
            "from_chain": "base",
            "to_chain": "base",
            "slippage_bps": 50,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_confirm_no_409_for_concurrent_swaps_enqueue_and_wait(
    client: TestClient, db: Session, monkeypatch
):
    """2 swaps concurrents → les 2 confirms réussissent (pas de fail-fast 409)."""
    from services.lifi.routes import _confirm_svc, _quote_svc

    pe = make_linked_client(db, email="eaw-confirm@example.com")
    _enable_enqueue_and_wait(monkeypatch, pe)
    _seed_wallet(db, pe)

    q1 = _post_quote(client, db, pe)
    q2 = _post_quote(client, db, pe)
    _confirm_svc._core._quote._lifi = _quote_svc._lifi

    def _confirm(swap_body):
        return client.post(
            "/api/swaps/confirm-execute",
            headers=_auth_headers(db, pe),
            json={
                "swap_id": swap_body["swap_id"],
                "review_estimated_receive": swap_body["estimated_receive"],
                "review_amount_in": swap_body["amount_in"],
            },
        )

    r1 = _confirm(q1)
    r2 = _confirm(q2)

    assert r1.status_code == 200, r1.text
    # Le 2e ne doit PAS être rejeté en 409 fail-fast (il est mis en file côté worker).
    assert r2.status_code != 409, r2.text
