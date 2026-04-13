"""Tests for GET /api/app/transactions/{transaction_id} (JWT)."""
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
    return f"txdetail-{uuid.uuid4().hex[:8]}@example.com"


def _setup_pipeline(http: TestClient, db: Session, *, email=None):
    """Provider + client PE lié + comptes."""
    prov_res = http.post(
        "/api/admin/custody/providers",
        json={"name": f"Bank-{uuid.uuid4().hex[:6]}", "provider_type": "bank", "jurisdiction": "EU"},
        headers=ADMIN_HEADERS,
    )
    assert prov_res.status_code == 201
    provider = prov_res.json()

    pe_client = make_linked_client(db, email=email or _unique_email())

    iban = f"DE{uuid.uuid4().hex[:16].upper()}"
    acc_res = http.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider["id"],
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "Test User",
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


def _simulate_deposit(http: TestClient, provider_name, iban, *, amount=1000, ref=None,
                      remitter_name=None, remitter_iban=None, narrative=None):
    ref = ref or f"TXDET-{uuid.uuid4().hex[:6]}"
    payload = {
        "event_type": "deposit_detected",
        "reference": ref,
        "iban": iban,
        "amount": amount,
        "currency": "EUR",
    }
    if remitter_name:
        payload["remitter_name"] = remitter_name
    if remitter_iban:
        payload["remitter_iban"] = remitter_iban
    if narrative:
        payload["narrative"] = narrative
    res = http.post(f"/api/webhooks/custody/{provider_name}", json=payload)
    assert res.status_code == 200
    return res.json(), ref


def test_transaction_detail_returns_deposit_info(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    result, ref = _simulate_deposit(
        client, provider["name"], client_account["iban"],
        amount=1500,
        remitter_name="Alice Martin",
        remitter_iban="FR7612345678901234567890123",
        narrative="Loyer mars 2026",
    )

    cash_res = client.get("/api/app/cash", headers=auth)
    assert cash_res.status_code == 200
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    detail_res = client.get(f"/api/app/transactions/{tx_id}", headers=auth)
    assert detail_res.status_code == 200
    data = detail_res.json()

    assert data["id"] == tx_id
    assert data["transaction_type"] == "deposit"
    assert data["direction"] == "credit"
    assert float(data["amount"]) == 1500.0
    assert data["currency"] == "EUR"
    assert data["currency_symbol"] == "€"
    assert data["status"] == "completed"
    assert data["title"] == "Virement entrant"
    assert data["status_label"] == "Complété"
    assert data["created_at"] is not None
    assert data["provider_name"] is not None


def test_transaction_detail_exposes_remitter_metadata(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(
        client, provider["name"], client_account["iban"],
        remitter_name="Bob Dupont",
        remitter_iban="DE89370400440532013000",
        narrative="Paiement facture 42",
    )

    cash_res = client.get("/api/app/cash", headers=auth)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    detail_res = client.get(f"/api/app/transactions/{tx_id}", headers=auth)
    assert detail_res.status_code == 200
    data = detail_res.json()

    assert data["remitter_name"] == "Bob Dupont"
    assert data["narrative"] == "Paiement facture 42"


def test_transaction_detail_masks_ibans(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(
        client, provider["name"], client_account["iban"],
        remitter_iban="FR7612345678901234567890123",
    )

    cash_res = client.get("/api/app/cash", headers=auth)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    detail_res = client.get(f"/api/app/transactions/{tx_id}", headers=auth)
    assert detail_res.status_code == 200
    data = detail_res.json()

    if data["remitter_iban"]:
        assert "****" in data["remitter_iban"]
        assert data["remitter_iban"] != "FR7612345678901234567890123"

    if data["target_iban"]:
        assert "****" in data["target_iban"]
        assert data["target_iban"] != client_account["iban"]


def test_transaction_detail_respects_ownership(client: TestClient, db: Session):
    provider, client_a, account_a = _setup_pipeline(client, db)
    auth_a = mobile_auth_headers(db, client_a)
    _simulate_deposit(client, provider["name"], account_a["iban"], amount=500)

    cash_res = client.get("/api/app/cash", headers=auth_a)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    _, client_b, _ = _setup_pipeline(client, db)
    auth_b = mobile_auth_headers(db, client_b)

    detail_res = client.get(f"/api/app/transactions/{tx_id}", headers=auth_b)
    assert detail_res.status_code == 404


def test_unknown_transaction_returns_404(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=_unique_email())
    auth = mobile_auth_headers(db, pe_client)

    fake_id = str(uuid.uuid4())
    detail_res = client.get(f"/api/app/transactions/{fake_id}", headers=auth)
    assert detail_res.status_code == 404
    assert "not found" in detail_res.json()["detail"].lower()
