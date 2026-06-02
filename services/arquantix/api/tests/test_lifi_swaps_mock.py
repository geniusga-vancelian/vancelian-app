"""Tests swap LI.FI en mode mock (local dev)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.routes import _execute_svc, _quote_svc
from services.lifi.config import build_lifi_client
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from tests.conftest import ensure_admin_for_linked_client, make_linked_client


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        from database import engine

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
PRIVY_USER = "did:privy:testswapmock001"


def _auth_headers(db: Session, client_id):
    user = ensure_admin_for_linked_client(db, client_id)
    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="swap-mock@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-mock"},
    )
    db.commit()


def test_supported_assets_exposes_mock_mode(client: TestClient, monkeypatch):
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    res = client.get("/api/swaps/supported-assets")
    assert res.status_code == 200
    assert res.json()["mock_mode"] is True


def test_mock_swap_quote_execute_and_settle(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    monkeypatch.delenv("LIFI_API_KEY", raising=False)

    mock_client = build_lifi_client()
    _quote_svc._lifi = mock_client
    _execute_svc._lifi = mock_client

    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    admin = PrivyWalletAdminService()
    admin.simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="1000",
            chain_id=1,
        ),
    )
    db.commit()

    headers = _auth_headers(db, pe)
    quote_res = client.post(
        "/api/swaps/quote",
        headers=headers,
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "10",
            "from_chain": "ethereum",
            "to_chain": "ethereum",
        },
    )
    assert quote_res.status_code == 200, quote_res.text
    quote = quote_res.json()
    assert quote["from_chain"] == "ethereum"
    assert Decimal(quote["estimated_receive"]) > 0

    swap_id = quote["swap_id"]
    exec_res = client.post("/api/swaps/execute", headers=headers, json={"swap_id": swap_id})
    assert exec_res.status_code == 200

    submit_res = client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=headers,
        json={"tx_hash": "0xmockdeadbeef"},
    )
    assert submit_res.status_code == 200, submit_res.text
    body = submit_res.json()
    assert body["status"] == "CONFIRMED"

    status_res = client.get(f"/api/swaps/{swap_id}", headers=headers)
    assert status_res.json()["status"] == "CONFIRMED"

    usdc_tx = client.get("/api/app/crypto-positions/USDC/transactions", headers=headers)
    assert usdc_tx.status_code == 200, usdc_tx.text
    usdc_titles = [t.get("title") for t in usdc_tx.json().get("transactions", [])]
    assert any("Échange USDC → ETH" in str(t) for t in usdc_titles)

    eth_tx = client.get("/api/app/crypto-positions/ETH/transactions", headers=headers)
    assert eth_tx.status_code == 200, eth_tx.text
    eth_titles = [t.get("title") for t in eth_tx.json().get("transactions", [])]
    assert any("Échange USDC → ETH" in str(t) for t in eth_titles)


def test_mock_swap_submit_creates_lifi_attempt_confirmed(client: TestClient, db: Session, monkeypatch):
    """Mock submit doit dual-writer l'attempt swap (Phase 2 forward), comme le chemin live."""
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    monkeypatch.delenv("LIFI_API_KEY", raising=False)

    mock_client = build_lifi_client()
    _quote_svc._lifi = mock_client
    _execute_svc._lifi = mock_client

    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="100",
            chain_id=8453,
        ),
    )
    db.commit()

    headers = _auth_headers(db, pe)
    quote_res = client.post(
        "/api/swaps/quote",
        headers=headers,
        json={
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "amount": "10",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert quote_res.status_code == 200, quote_res.text
    swap_id = quote_res.json()["swap_id"]
    mock_tx = "0xmock_lifi_attempt_e2e"

    client.post("/api/swaps/execute", headers=headers, json={"swap_id": swap_id})
    submit_res = client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=headers,
        json={"tx_hash": mock_tx},
    )
    assert submit_res.status_code == 200, submit_res.text
    assert submit_res.json()["status"] == "CONFIRMED"

    from services.transaction_attempts.enums import AttemptProtocol, AttemptStepType
    from services.transaction_attempts.models import OnchainTransactionAttempt

    attempts = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.person_id == pe.person_id,
            OnchainTransactionAttempt.protocol == AttemptProtocol.LIFI.value,
        )
        .all()
    )
    swap_attempts = [a for a in attempts if a.step_type == AttemptStepType.SWAP.value]
    assert len(swap_attempts) == 1
    attempt = swap_attempts[0]
    assert attempt.status == "confirmed"
    assert attempt.tx_hash == mock_tx.lower()
    assert attempt.linked_table == "person_wallet_swaps"
    assert str(attempt.linked_id) == swap_id

    from services.transaction_attempts.reconciliation import build_gap_report

    gap = build_gap_report(db, person_id=pe.person_id, person_limit=1)
    blocking = gap.get("summary", {}).get("blocking_gaps", gap.get("summary", {}).get("total_gaps", 0))
    swap_missing = [
        g for g in gap.get("gaps", []) if g.get("gap_type") == "swap_missing_swap_attempt"
    ]
    assert swap_missing == []
    assert blocking == 0


def test_mock_swap_dual_write_idempotent(client: TestClient, db: Session, monkeypatch):
    """Second appel dual_write confirm sur le même swap mock ne duplique pas l'attempt."""
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    monkeypatch.delenv("LIFI_API_KEY", raising=False)

    mock_client = build_lifi_client()
    _quote_svc._lifi = mock_client
    _execute_svc._lifi = mock_client

    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="50",
            chain_id=8453,
        ),
    )
    db.commit()

    headers = _auth_headers(db, pe)
    quote_res = client.post(
        "/api/swaps/quote",
        headers=headers,
        json={
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "amount": "5",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    swap_id = quote_res.json()["swap_id"]
    mock_tx = "0xmock_idempotent_swap"

    client.post("/api/swaps/execute", headers=headers, json={"swap_id": swap_id})
    client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=headers,
        json={"tx_hash": mock_tx},
    )

    from services.lifi.models import PersonWalletSwap
    from services.transaction_attempts.dual_write import dual_write_lifi_swap_confirmed
    from services.transaction_attempts.models import OnchainTransactionAttempt

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).one()
    dual_write_lifi_swap_confirmed(db, swap, tx_hash=mock_tx)
    db.commit()

    count = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.person_id == pe.person_id,
            OnchainTransactionAttempt.tx_hash == mock_tx.lower(),
        )
        .count()
    )
    assert count == 1
