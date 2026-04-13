"""Tests for the end-to-end webhook deposit → cash endpoint pipeline (JWT)."""
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
    return f"cash-e2e-{uuid.uuid4().hex[:8]}@example.com"


def _setup_full_pipeline(http: TestClient, db: Session):
    """Create provider, linked PE client, client account, settlement account."""
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


def test_webhook_deposit_updates_balance(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)

    ref = f"E2E-DEP-{uuid.uuid4().hex[:6]}"
    webhook_res = client.post(
        f"/api/webhooks/custody/{provider['name']}",
        json={
            "event_type": "deposit_detected",
            "reference": ref,
            "iban": client_account["iban"],
            "amount": 1000,
            "currency": "EUR",
        },
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["processing_status"] == "processed"

    cash_res = client.get("/api/app/cash", headers=auth)
    assert cash_res.status_code == 200
    data = cash_res.json()

    assert data["client"]["id"] == str(pe_client.id)
    assert data["cash_account"] is not None
    assert float(data["cash_account"]["available_balance"]) >= 1000.0


def test_duplicate_webhook_not_applied(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)

    ref = f"E2E-DUP-{uuid.uuid4().hex[:6]}"
    payload = {
        "event_type": "deposit_detected",
        "reference": ref,
        "iban": client_account["iban"],
        "amount": 500,
        "currency": "EUR",
    }

    r1 = client.post(f"/api/webhooks/custody/{provider['name']}", json=payload)
    assert r1.status_code == 200
    assert r1.json()["processing_status"] == "processed"

    cash_after_first = client.get("/api/app/cash", headers=auth).json()
    balance_after_first = float(cash_after_first["cash_account"]["available_balance"])

    r2 = client.post(f"/api/webhooks/custody/{provider['name']}", json=payload)
    assert r2.status_code == 200
    assert r2.json()["processing_status"] == "duplicate"

    cash_after_second = client.get("/api/app/cash", headers=auth).json()
    balance_after_second = float(cash_after_second["cash_account"]["available_balance"])

    assert balance_after_second == balance_after_first


def test_cash_endpoint_returns_balance(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_full_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)

    ref = f"E2E-STRUCT-{uuid.uuid4().hex[:6]}"
    client.post(
        f"/api/webhooks/custody/{provider['name']}",
        json={
            "event_type": "deposit_detected",
            "reference": ref,
            "iban": client_account["iban"],
            "amount": 2500,
            "currency": "EUR",
        },
    )

    cash_res = client.get("/api/app/cash", headers=auth)
    assert cash_res.status_code == 200
    data = cash_res.json()

    assert "client" in data
    assert data["client"]["id"] == str(pe_client.id)
    assert data["client"]["email"] == pe_client.email

    assert "cash_account" in data
    ca = data["cash_account"]
    assert ca["currency"] == "EUR"
    assert ca["account_id"] is not None
    assert "****" in (ca["iban"] or "")

    assert "recent_transactions" in data
    assert len(data["recent_transactions"]) >= 1
    tx = data["recent_transactions"][0]
    assert tx["type"] == "deposit"
    assert tx["direction"] == "credit"
    assert tx["status"] == "completed"
    assert float(tx["amount"]) > 0
    assert "created_at" in tx
