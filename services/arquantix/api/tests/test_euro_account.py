"""Tests for GET /api/app/euro-account endpoint (JWT → PeClient)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


def _unique_email():
    return f"euro-e2e-{uuid.uuid4().hex[:8]}@example.com"


def _setup_full_pipeline(http: TestClient, db: Session):
    """Create provider, linked PE client, client EUR account, settlement account."""
    prov_res = http.post(
        "/api/admin/custody/providers",
        json={"name": f"Bank-{uuid.uuid4().hex[:6]}", "provider_type": "bank", "jurisdiction": "EU"},
        headers=ADMIN_HEADERS,
    )
    assert prov_res.status_code == 201
    provider = prov_res.json()

    pe_client = make_linked_client(db, email=_unique_email())

    iban = f"DE{uuid.uuid4().hex[:16].upper()}"
    acc_res = http.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider["id"],
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "Test User EUR",
            "client_id": str(pe_client.id),
            "iban": iban,
        },
        headers=custody_admin_headers(db),
    )
    assert acc_res.status_code == 201
    client_account = acc_res.json()

    settle_res = http.post(
        "/api/admin/custody/accounts/settlement",
        json={
            "provider_id": provider["id"],
            "account_type": "company_settlement_account",
            "currency": "EUR",
            "account_holder_name": "Vancelian SA",
            "is_master_account": True,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=custody_admin_headers(db),
    )
    if settle_res.status_code != 409:
        assert settle_res.status_code == 201

    return provider, pe_client, client_account


def _simulate_deposit(http, provider_name, iban, amount, ref=None):
    """Send a simulated webhook deposit and return the response."""
    ref = ref or f"EUR-DEP-{uuid.uuid4().hex[:6]}"
    return http.post(
        f"/api/webhooks/custody/{provider_name}",
        json={
            "event_type": "deposit_detected",
            "reference": ref,
            "iban": iban,
            "amount": amount,
            "currency": "EUR",
            "remitter_name": "Jean Dupont",
            "narrative": "Virement test",
        },
    )


def test_euro_account_returns_balance(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)

    _simulate_deposit(client, provider["name"], client_account["iban"], 1500)

    res = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, pe_client))
    assert res.status_code == 200
    data = res.json()

    assert data["client"]["id"] == str(pe_client.id)
    assert data["account"] is not None
    assert data["account"]["currency"] == "EUR"
    assert data["account"]["currency_symbol"] == "€"
    assert float(data["account"]["balance"]) >= 1500.0
    assert data["account"]["account_holder_name"] == "Test User EUR"


def test_euro_account_iban_masked(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)

    res = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, pe_client))
    assert res.status_code == 200
    data = res.json()

    iban = data["account"]["iban_masked"]
    assert iban is not None
    assert "****" in iban
    assert len(iban) == 12


def test_euro_account_transactions_sorted_desc(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)

    _simulate_deposit(client, provider["name"], client_account["iban"], 100)
    _simulate_deposit(client, provider["name"], client_account["iban"], 200)

    res = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, pe_client))
    assert res.status_code == 200
    data = res.json()

    txs = data["transactions"]
    assert len(txs) >= 2

    dates = [tx["created_at"] for tx in txs]
    assert dates == sorted(dates, reverse=True)


def test_euro_account_deposit_fields(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)

    _simulate_deposit(client, provider["name"], client_account["iban"], 750)

    res = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, pe_client))
    assert res.status_code == 200
    data = res.json()

    assert len(data["transactions"]) >= 1
    tx = data["transactions"][0]

    assert tx["transaction_type"] == "deposit"
    assert tx["transaction_kind"] == "bank_transfer_in"
    assert tx["direction"] == "credit"
    assert tx["status"] == "completed"
    assert tx["title"] == "Virement entrant"
    assert tx["subtitle"] == "Jean Dupont"
    assert tx["currency"] == "EUR"
    assert tx["currency_symbol"] == "€"
    assert float(tx["amount"]) == 750.0
    assert tx["remitter_name"] == "Jean Dupont"


def test_euro_account_ownership(client: TestClient, db: Session):
    provider, client_a, account_a = _setup_full_pipeline(client, db)

    _simulate_deposit(client, provider["name"], account_a["iban"], 1000)

    _, client_b, _ = _setup_full_pipeline(client, db)

    res_b = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, client_b))
    assert res_b.status_code == 200
    data = res_b.json()

    assert data["client"]["id"] == str(client_b.id)
    if data["account"] is not None:
        for tx in data["transactions"]:
            assert tx["currency"] == "EUR"


def test_euro_account_no_account(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=_unique_email())

    res = client.get("/api/app/euro-account", headers=mobile_auth_headers(db, pe_client))
    assert res.status_code == 200
    data = res.json()

    assert data["client"]["id"] == str(pe_client.id)
    assert data["account"] is None
    assert data["transactions"] == []


def test_euro_account_requires_auth(client: TestClient):
    res = client.get("/api/app/euro-account")
    assert res.status_code == 401
