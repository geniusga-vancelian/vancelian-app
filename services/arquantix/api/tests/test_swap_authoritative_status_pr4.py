"""PR4 — signaux front du mode autoritaire / enqueue-and-wait.

Couvre : (1) confirm-execute expose server_authoritative + intent_id en mode autoritaire,
(2) compute_swap_queue_state mappe correctement statut swap + slot global vers l'étape file.
"""
from __future__ import annotations

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
from services.lifi.swap_queue_state import (
    QUEUE_STATE_COMPLETED,
    QUEUE_STATE_CONFIRMING,
    QUEUE_STATE_EXECUTING,
    QUEUE_STATE_FAILED,
    QUEUE_STATE_PREPARING,
    QUEUE_STATE_WAITING,
    compute_swap_queue_state,
)
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.financial_transaction_global_lock import (
    acquire_financial_transaction_global_lock_or_raise,
)
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
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


def _enable_authoritative(monkeypatch, pe) -> None:
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("LIFI_ENQUEUE_AND_WAIT_ENABLED", "true")
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")


def _seed_swap(db: Session, pe, *, status: str, to_asset: str = "AAVE"):
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
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
    db.commit()
    db.refresh(swap)
    db.refresh(intent)
    return swap, intent


# --------------------------------------------------------------- queue state


def test_queue_state_terminal(db: Session, monkeypatch):
    pe = make_linked_client(db, email="q-term@example.com")
    _enable_authoritative(monkeypatch, pe)
    _seed_wallet(db, pe)

    confirmed, _ = _seed_swap(db, pe, status=SwapSessionStatus.CONFIRMED.value, to_asset="AAVE")
    assert compute_swap_queue_state(db, confirmed, person_id=pe.person_id) == QUEUE_STATE_COMPLETED

    failed, _ = _seed_swap(db, pe, status=SwapSessionStatus.FAILED.value, to_asset="ETH")
    assert compute_swap_queue_state(db, failed, person_id=pe.person_id) == QUEUE_STATE_FAILED


def test_queue_state_in_flight(db: Session, monkeypatch):
    pe = make_linked_client(db, email="q-flight@example.com")
    _enable_authoritative(monkeypatch, pe)
    _seed_wallet(db, pe)

    submitted, _ = _seed_swap(db, pe, status=SwapSessionStatus.SUBMITTED.value, to_asset="AAVE")
    assert compute_swap_queue_state(db, submitted, person_id=pe.person_id) == QUEUE_STATE_CONFIRMING

    broadcasting, _ = _seed_swap(db, pe, status=SwapSessionStatus.BROADCASTING.value, to_asset="ETH")
    assert compute_swap_queue_state(db, broadcasting, person_id=pe.person_id) == QUEUE_STATE_EXECUTING


def test_queue_state_preparing_when_no_lock(db: Session, monkeypatch):
    pe = make_linked_client(db, email="q-prep@example.com")
    _enable_authoritative(monkeypatch, pe)
    _seed_wallet(db, pe)

    swap, _ = _seed_swap(db, pe, status=SwapSessionStatus.AWAITING_SIGNATURE.value)
    assert compute_swap_queue_state(db, swap, person_id=pe.person_id) == QUEUE_STATE_PREPARING


def test_queue_state_waiting_when_other_intent_holds_lock(db: Session, monkeypatch):
    pe = make_linked_client(db, email="q-wait@example.com")
    _enable_authoritative(monkeypatch, pe)
    _seed_wallet(db, pe)

    # swap A détient le slot user
    _swap_a, intent_a = _seed_swap(db, pe, status=SwapSessionStatus.BROADCASTING.value, to_asset="AAVE")
    acquire_financial_transaction_global_lock_or_raise(
        db, person_id=pe.person_id, intent_id=intent_a.id, reason="lifi_swap"
    )
    db.commit()

    # swap B en pré-exécution → en file derrière A
    swap_b, _ = _seed_swap(db, pe, status=SwapSessionStatus.QUOTE_RECEIVED.value, to_asset="ETH")
    assert compute_swap_queue_state(db, swap_b, person_id=pe.person_id) == QUEUE_STATE_WAITING


# --------------------------------------------------------------- confirm-execute signal


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


def test_confirm_execute_exposes_server_authoritative(client: TestClient, db: Session, monkeypatch):
    from services.lifi.routes import _confirm_svc, _quote_svc

    pe = make_linked_client(db, email="confirm-auth@example.com")
    _enable_authoritative(monkeypatch, pe)
    _seed_wallet(db, pe)

    q = _post_quote(client, db, pe)
    _confirm_svc._core._quote._lifi = _quote_svc._lifi

    res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": q["swap_id"],
            "review_estimated_receive": q["estimated_receive"],
            "review_amount_in": q["amount_in"],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["server_authoritative"] is True
    assert body["intent_id"]


def test_confirm_execute_not_authoritative_when_flag_off(client: TestClient, db: Session, monkeypatch):
    from services.lifi.routes import _confirm_svc, _quote_svc

    pe = make_linked_client(db, email="confirm-noauth@example.com")
    _enable_authoritative(monkeypatch, pe)
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "false")
    _seed_wallet(db, pe)

    q = _post_quote(client, db, pe)
    _confirm_svc._core._quote._lifi = _quote_svc._lifi

    res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": q["swap_id"],
            "review_estimated_receive": q["estimated_receive"],
            "review_amount_in": q["amount_in"],
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["server_authoritative"] is False
