"""Allowlist pilot prod — orchestrateur limité à des personnes explicites (fail-closed)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient
from services.lifi.lifi_swap_settlement import apply_swap_settlement
from services.lifi.routes import _quote_svc
from services.onchain_indexer.models import TransactionIntent
from services.settlement.lifi_ledger import count_swap_settlement_legs
from services.settlement.result import SettlementOutcome
from services.settlement.settle import settle_transaction_intent_idempotently
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from tests.test_lifi_swap_routes import _auth_headers, _mock_lifi_quote, _seed_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def _seed_privy_wallet(db: Session, pe) -> None:
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"privy-{pe.person_id}",
        external_email=pe.email,
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-allowlist"},
    )
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="10",
            chain_id=8453,
        ),
    )


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
    reason="Migration 173 requise.",
)


def _post_quote(client: TestClient, db: Session, pe) -> tuple[int, dict]:
    mock_client = MagicMock(spec=LifiClient)
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
    body = res.json() if res.content else {}
    return res.status_code, body


def test_allowlisted_user_orchestrator_when_flags_on(
    client: TestClient, db: Session, monkeypatch
):
    """S2a.2 — quote seul : pas d'intent ; confirm crée intent orchestrateur + outbox."""
    from services.lifi.routes import _confirm_svc

    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    pe = make_linked_client(db, email="pilot-allowlisted@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    _seed_wallet(db, pe)

    status_code, body = _post_quote(client, db, pe)
    assert status_code == 200

    intent_after_quote = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == body["swap_id"],
        )
        .first()
    )
    assert intent_after_quote is None

    _confirm_svc._quote._lifi = _quote_svc._lifi
    confirm_res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": body["swap_id"],
            "review_estimated_receive": body["estimated_receive"],
            "review_amount_in": body["amount_in"],
        },
    )
    assert confirm_res.status_code == 200, confirm_res.text

    intent = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.linked_table == "person_wallet_swaps",
            TransactionIntent.linked_id == body["swap_id"],
        )
        .one()
    )
    assert (intent.metadata_json or {}).get("phase2_orchestrator") is True
    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert len(events) == 1


def test_non_allowlisted_user_legacy_when_flags_on(
    client: TestClient, db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "other-pilot@example.com")

    pe = make_linked_client(db, email="not-on-allowlist@example.com")
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
    events = TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
    assert events == []
    assert TransactionOutboxRepository.count_all(db) == outbox_before


def test_flags_on_empty_allowlist_fail_closed_legacy(
    client: TestClient, db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.delenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", raising=False)

    pe = make_linked_client(db, email="anyone@example.com")
    _seed_wallet(db, pe)

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
    assert (
        TransactionOutboxRepository.find_by_intent(db, intent.id, event_type="intent.created")
        == []
    )


def test_settlement_ledger_skips_non_allowlisted_apply_swap_legacy(
    db: Session, monkeypatch
):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "other@example.com")

    pe = make_linked_client(db, email="legacy-user@example.com")
    _seed_privy_wallet(db, pe)

    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
    )
    swap = bundle.swap
    swap.status = SwapSessionStatus.CONFIRMED.value
    swap.estimated_receive = Decimal("0.001")
    swap.tx_hash = "0xallowlistlegacyabcdef1234567890abcdef1234567890abcdef1234567890"
    swap.audit_log = [{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}]
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    db.commit()

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()
    assert result.outcome == SettlementOutcome.SUCCESS
    assert count_swap_settlement_legs(db, swap_id=swap.id, person_id=pe.person_id) == {
        "debit": 0,
        "credit": 0,
    }

    apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("0.001"))
    db.commit()
    assert count_swap_settlement_legs(db, swap_id=swap.id, person_id=pe.person_id) == {
        "debit": 1,
        "credit": 1,
    }
