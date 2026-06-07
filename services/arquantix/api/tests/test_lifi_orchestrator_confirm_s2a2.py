"""Phase 2 S2a.2 — intent orchestrateur au confirm_execute, pas au quote."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.lifi.config import lifi_outbox_worker_enabled
from services.lifi.lifi_client import LifiClient
from services.lifi.routes import _confirm_svc, _quote_svc
from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.cost_basis.models import CostBasisExecution
from services.portfolio_engine.positions.models import PositionAtom
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_orchestrator_quote_s2a import _post_quote
from tests.test_lifi_swap_routes import _auth_headers, _seed_wallet


def _mock_lifi_quote(*, to_amount: str = "450000000000000000"):
    return {
        "id": "quote-s2a2",
        "tool": "stargateV2",
        "action": {"fromChainId": 8453, "toChainId": 8453},
        "estimate": {
            "toAmount": to_amount,
            "toAmountMin": to_amount,
            "executionDuration": 120,
            "feeCosts": [],
        },
        "transactionRequest": {
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xdeadbeef",
            "value": "0",
            "chainId": 8453,
        },
    }


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
    pytest.mark.skipif(not _migration_159_applied(), reason="Migration 159 requise."),
    pytest.mark.skipif(not _migration_173_ready(), reason="Migration 173 requise."),
]


def _wire_lifi_mock(monkeypatch, *, to_amount: str = "450000000000000000"):
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount=to_amount)
    _quote_svc._lifi = mock_client
    _confirm_svc._quote._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    return mock_client


def _post_confirm(client: TestClient, db: Session, pe, *, swap_id: str, quote_body: dict) -> tuple[int, dict]:
    res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": swap_id,
            "review_estimated_receive": quote_body["estimated_receive"],
            "review_amount_in": quote_body["amount_in"],
        },
    )
    body = res.json() if res.content else {}
    return res.status_code, body


def _economic_snapshot(db: Session, person_id) -> tuple[int, int, int, int]:
    balances = db.query(PersonWalletBalance).filter(PersonWalletBalance.person_id == person_id).count()
    deposits = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == person_id).count()
    pe = db.query(PositionAtom).count()
    cb = db.query(CostBasisExecution).count()
    return balances, deposits, pe, cb


def test_s2a2_quote_no_intent_or_outbox(client: TestClient, db: Session, monkeypatch):
    """Orchestrateur ON — /quote crée swap uniquement, 0 intent / 0 outbox."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _wire_lifi_mock(monkeypatch)
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)

    intents_before = db.query(TransactionIntent).count()
    outbox_before = TransactionOutboxRepository.count_all(db)

    status_code, body = _post_quote(client, db, pe)
    assert status_code == 200
    swap_id = UUID(str(body["swap_id"]))

    assert db.query(TransactionIntent).count() == intents_before
    assert TransactionOutboxRepository.count_all(db) == outbox_before

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == swap_id,
        )
        .first()
    )
    assert intent is None


def test_s2a2_confirm_creates_intent_and_outbox(client: TestClient, db: Session, monkeypatch):
    """Orchestrateur ON — confirm_execute crée 1 intent + 1 outbox intent.created."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _wire_lifi_mock(monkeypatch)
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)
    bal0, dep0, pe0, cb0 = _economic_snapshot(db, pe.person_id)

    status_code, quote_body = _post_quote(client, db, pe)
    assert status_code == 200
    swap_id = quote_body["swap_id"]

    confirm_status, confirm_body = _post_confirm(client, db, pe, swap_id=swap_id, quote_body=quote_body)
    assert confirm_status == 200, confirm_body
    assert confirm_body["execute"]["status"] == "AWAITING_SIGNATURE"

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == UUID(swap_id),
        )
        .one()
    )
    assert intent.status == "created"
    assert intent.current_phase == "CREATED"
    assert (intent.metadata_json or {}).get("phase2_orchestrator") is True
    assert (intent.metadata_json or {}).get("s2a2_confirm_attach") is True

    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert len(events) == 1
    assert events[0].status == "pending"
    assert (events[0].payload_json or {}).get("swap_id") == swap_id

    bal1, dep1, pe1, cb1 = _economic_snapshot(db, pe.person_id)
    assert (bal1, dep1, pe1, cb1) == (bal0, dep0, pe0, cb0)

    completed = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.current_phase == "COMPLETED")
        .count()
    )
    assert completed == 0


def test_s2a2_double_confirm_idempotent(client: TestClient, db: Session, monkeypatch):
    """Double confirm_execute — pas de double intent/outbox."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _wire_lifi_mock(monkeypatch)
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)

    status_code, quote_body = _post_quote(client, db, pe)
    assert status_code == 200
    swap_id = quote_body["swap_id"]

    first_status, _ = _post_confirm(client, db, pe, swap_id=swap_id, quote_body=quote_body)
    assert first_status == 200

    intent_count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == UUID(swap_id),
        )
        .count()
    )
    outbox_count = db.query(TransactionOutbox).count()

    second_status, _ = _post_confirm(client, db, pe, swap_id=swap_id, quote_body=quote_body)
    assert second_status == 200

    assert (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == UUID(swap_id),
        )
        .count()
        == intent_count
    )
    assert db.query(TransactionOutbox).count() == outbox_count


def test_s2a2_confirm_price_changed_no_intent(client: TestClient, db: Session, monkeypatch):
    """Slippage rejeté (409) — pas d'intent créé."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    mock_client = _wire_lifi_mock(monkeypatch, to_amount="450000000000000000")
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)

    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount="450000000000000000")
    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1000",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert res.status_code == 200, res.text
    quote_body = res.json()
    swap_id = quote_body["swap_id"]

    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount="400000000000000000")
    confirm_res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": swap_id,
            "review_estimated_receive": quote_body["estimated_receive"],
        },
    )
    assert confirm_res.status_code == 409, confirm_res.text

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == UUID(swap_id),
        )
        .first()
    )
    assert intent is None


def test_s2a2_non_allowlist_legacy_unchanged(client: TestClient, db: Session, monkeypatch):
    """Flags ON + user hors allowlist — quote crée intent miroir legacy, pas outbox orchestrateur."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _wire_lifi_mock(monkeypatch)
    pe = make_linked_client(db)
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "other-user@example.com")
    _seed_wallet(db, pe)
    outbox_before = TransactionOutboxRepository.count_all(db)

    status_code, body = _post_quote(client, db, pe)
    assert status_code == 200

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == body["swap_id"],
        )
        .one()
    )
    assert (intent.metadata_json or {}).get("phase2_orchestrator") is not True
    assert TransactionOutboxRepository.count_all(db) == outbox_before


def test_s2a2_worker_off_outbox_stays_pending(client: TestClient, db: Session, monkeypatch):
    """Worker OFF — outbox intent.created reste pending après confirm."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.delenv("LIFI_OUTBOX_WORKER_ENABLED", raising=False)
    assert lifi_outbox_worker_enabled() is False

    _wire_lifi_mock(monkeypatch)
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)

    status_code, quote_body = _post_quote(client, db, pe)
    assert status_code == 200

    confirm_status, _ = _post_confirm(client, db, pe, swap_id=quote_body["swap_id"], quote_body=quote_body)
    assert confirm_status == 200

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == UUID(quote_body["swap_id"]),
        )
        .one()
    )
    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert len(events) == 1
    assert events[0].status == "pending"
    assert events[0].attempt_count == 0
