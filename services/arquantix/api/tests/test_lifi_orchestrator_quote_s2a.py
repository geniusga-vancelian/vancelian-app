"""Phase 2 S2a — quote → intent orchestrateur → outbox intent.created (flag ON).

Legacy inchangé si LIFI_INTENT_ORCHESTRATOR_ENABLED=false (défaut).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from uuid import UUID

from database import engine
from services.lifi.lifi_client import LifiClient
from services.lifi.routes import _quote_svc
from services.onchain_indexer.models import TransactionIntent
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.test_lifi_swap_routes import _auth_headers, _mock_lifi_quote, _seed_wallet


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


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _migration_159_applied(), reason="Migration 159 (person_wallet_swaps) requise."),
    pytest.mark.skipif(not _migration_173_ready(), reason="Migration 173 (transaction_outbox) requise."),
]


def _post_quote(client: TestClient, db: Session, pe) -> dict:
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client

    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "100",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_s2a_legacy_quote_no_orchestrator_outbox(
    client: TestClient, db: Session, monkeypatch
):
    """Flag OFF (défaut) — intent miroir Phase 7, pas d'outbox intent.created."""
    monkeypatch.delenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", raising=False)
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    outbox_before = TransactionOutboxRepository.count_all(db)

    body = _post_quote(client, db, pe)

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == body["swap_id"],
        )
        .one()
    )
    assert (intent.metadata_json or {}).get("phase2_orchestrator") is not True

    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert events == []
    assert TransactionOutboxRepository.count_all(db) == outbox_before


def test_s2a_orchestrator_quote_creates_intent_and_outbox(
    client: TestClient, db: Session, monkeypatch
):
    """Flag ON — quote crée intent orchestrateur + outbox intent.created (même TX)."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    body = _post_quote(client, db, pe)
    swap_id = UUID(str(body["swap_id"]))

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == swap_id,
        )
        .one()
    )
    assert intent.status == "created"
    assert intent.current_phase == "CREATED"
    assert intent.idempotency_key == f"lifi_swap:{swap_id}"
    assert (intent.metadata_json or {}).get("phase2_orchestrator") is True
    assert (intent.metadata_json or {}).get("s2a_quote_bootstrap") is True

    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert len(events) == 1
    outbox = events[0]
    assert outbox.status == "pending"
    assert outbox.correlation_id == intent.correlation_id
    assert (outbox.payload_json or {}).get("swap_id") == str(swap_id)

    assert db.query(TransactionOutbox).filter(TransactionOutbox.intent_id == intent.id).count() == 1


def test_s2a_intent_sync_bypass_when_orchestrator_enabled(db: Session, monkeypatch):
    """sync_lifi_swap_intent no-op si orchestrateur actif (évite double intent)."""
    from uuid import uuid4

    from services.lifi.models import PersonWalletSwap
    from services.transaction_intents.lifi_intent_sync import sync_lifi_swap_intent

    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    pe = make_linked_client(db)
    before = db.query(TransactionIntent).count()

    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status="QUOTE_RECEIVED",
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        audit_log=[],
    )
    db.add(swap)
    db.flush()

    sync_lifi_swap_intent(db, swap)
    db.flush()

    assert db.query(TransactionIntent).count() == before
