"""Tests for Simulated BAS Deposit (JWT + custody admin)."""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


def _unique_email():
    return f"sim-dep-{uuid.uuid4().hex[:8]}@example.com"


def _create_provider(http: TestClient):
    r = http.post(
        "/api/admin/custody/providers",
        json={"name": f"Bank-{uuid.uuid4().hex[:6]}", "provider_type": "bank", "jurisdiction": "EU"},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 201
    return r.json()


def _create_client_account(http, provider_id: str, client_id: str, db: Session):
    iban = f"DE{uuid.uuid4().hex[:16].upper()}"
    r = http.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider_id,
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "Test User",
            "client_id": client_id,
            "iban": iban,
        },
        headers=custody_admin_headers(db),
    )
    assert r.status_code == 201
    return r.json()


def _ensure_settlement(http: TestClient, provider_id: str, db: Session):
    r = http.post(
        "/api/admin/custody/accounts/settlement",
        json={
            "provider_id": provider_id,
            "account_type": "company_settlement_account",
            "currency": "EUR",
            "account_holder_name": "Vancelian SA",
            "is_master_account": True,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=custody_admin_headers(db),
    )
    assert r.status_code in (201, 409)


def _setup(http: TestClient, db: Session):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    auth = mobile_auth_headers(db, pe_client)
    account = _create_client_account(http, provider["id"], str(pe_client.id), db)
    _ensure_settlement(http, provider["id"], db)
    return provider, pe_client, account, auth


def _webhook_deposit(http, provider_name, iban, amount, ref=None, **extra):
    ref = ref or f"SIM_DEP_{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "event_type": "deposit_detected",
        "reference": ref,
        "iban": iban,
        "amount": amount,
        "currency": "EUR",
        **extra,
    }
    r = http.post(f"/api/webhooks/custody/{provider_name}", json=payload)
    return r, ref


def test_simulate_deposit_for_selected_client(client: TestClient, db: Session):
    provider, pe_client, account, auth = _setup(client, db)

    r, ref = _webhook_deposit(
        client, provider["name"], account["iban"], 1000,
        remitter_name="Jean Dupont", narrative="Alimenter compte",
    )
    assert r.status_code == 200
    assert r.json()["processing_status"] == "processed"

    cash = client.get("/api/app/cash", headers=auth).json()
    assert float(cash["cash_account"]["available_balance"]) >= 1000.0


def test_deposit_updates_selected_client_balance_only(client: TestClient, db: Session):
    provider = _create_provider(client)
    _ensure_settlement(client, provider["id"], db)

    client_a = make_linked_client(db, email=_unique_email())
    account_a = _create_client_account(client, provider["id"], str(client_a.id), db)
    auth_a = mobile_auth_headers(db, client_a)

    client_b = make_linked_client(db, email=_unique_email())
    account_b = _create_client_account(client, provider["id"], str(client_b.id), db)
    auth_b = mobile_auth_headers(db, client_b)

    _webhook_deposit(client, provider["name"], account_a["iban"], 2000)

    cash_b = client.get("/api/app/cash", headers=auth_b).json()
    balance_b = float(cash_b["cash_account"]["available_balance"])
    assert balance_b == 0.0

    cash_a = client.get("/api/app/cash", headers=auth_a).json()
    assert float(cash_a["cash_account"]["available_balance"]) >= 2000.0


def test_deposit_transaction_stores_remitter_metadata(client: TestClient, db: Session):
    provider, pe_client, account, auth = _setup(client, db)

    _webhook_deposit(
        client, provider["name"], account["iban"], 500,
        remitter_name="Marie Martin",
        remitter_iban="FR7630006000011234567890189",
        narrative="Virement mensuel",
        booking_date="2026-03-15",
        value_date="2026-03-15",
    )

    r = client.get(
        f"/api/admin/custody/transactions?client_id={pe_client.id}",
        headers=custody_admin_headers(db),
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1

    tx = items[0]
    meta = tx.get("metadata_") or {}
    assert meta.get("remitter_name") == "Marie Martin"
    assert meta.get("remitter_iban") == "FR7630006000011234567890189"
    assert meta.get("narrative") == "Virement mensuel"


def test_duplicate_deposit_ignored(client: TestClient, db: Session):
    provider, pe_client, account, auth = _setup(client, db)

    ref = f"DUP_{uuid.uuid4().hex[:8].upper()}"
    r1, _ = _webhook_deposit(client, provider["name"], account["iban"], 750, ref=ref)
    assert r1.json()["processing_status"] == "processed"

    cash_1 = client.get("/api/app/cash", headers=auth).json()
    bal_1 = float(cash_1["cash_account"]["available_balance"])

    r2, _ = _webhook_deposit(client, provider["name"], account["iban"], 750, ref=ref)
    assert r2.json()["processing_status"] == "duplicate"

    cash_2 = client.get("/api/app/cash", headers=auth).json()
    bal_2 = float(cash_2["cash_account"]["available_balance"])
    assert bal_2 == bal_1


def test_admin_transaction_listing_filter_by_client(client: TestClient, db: Session):
    provider = _create_provider(client)
    _ensure_settlement(client, provider["id"], db)

    client_a = make_linked_client(db, email=_unique_email())
    account_a = _create_client_account(client, provider["id"], str(client_a.id), db)

    client_b = make_linked_client(db, email=_unique_email())
    account_b = _create_client_account(client, provider["id"], str(client_b.id), db)

    _webhook_deposit(client, provider["name"], account_a["iban"], 100)
    _webhook_deposit(client, provider["name"], account_b["iban"], 200)

    hdr = custody_admin_headers(db)
    r_a = client.get(
        f"/api/admin/custody/transactions?client_id={client_a.id}",
        headers=hdr,
    )
    assert r_a.status_code == 200
    items_a = r_a.json()["items"]
    for tx in items_a:
        assert tx["client_email"] == client_a.email

    r_b = client.get(
        f"/api/admin/custody/transactions?client_id={client_b.id}",
        headers=hdr,
    )
    assert r_b.status_code == 200
    items_b = r_b.json()["items"]
    for tx in items_b:
        assert tx["client_email"] == client_b.email


def test_cash_endpoint_returns_updated_balance(client: TestClient, db: Session):
    provider, pe_client, account, auth = _setup(client, db)

    _webhook_deposit(client, provider["name"], account["iban"], 3000)
    cash = client.get("/api/app/cash", headers=auth).json()
    assert float(cash["cash_account"]["available_balance"]) >= 3000.0

    _webhook_deposit(client, provider["name"], account["iban"], 500)
    cash2 = client.get("/api/app/cash", headers=auth).json()
    assert float(cash2["cash_account"]["available_balance"]) >= 3500.0


def test_cash_endpoint_exposes_deposit_metadata(client: TestClient, db: Session):
    provider, pe_client, account, auth = _setup(client, db)

    _webhook_deposit(
        client, provider["name"], account["iban"], 100,
        remitter_name="Paul Vancelian",
        narrative="Test virement",
    )

    cash = client.get("/api/app/cash", headers=auth).json()
    txs = cash["recent_transactions"]
    assert len(txs) >= 1

    tx = txs[0]
    assert tx["type"] == "deposit"
    assert tx["direction"] == "credit"
    assert tx["status"] == "completed"
    assert tx.get("remitter_name") == "Paul Vancelian"
    assert tx.get("narrative") == "Test virement"
    assert tx.get("provider") is not None


def test_error_if_client_has_no_eur_account(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=_unique_email())
    auth = mobile_auth_headers(db, pe_client)

    cash = client.get("/api/app/cash", headers=auth)
    assert cash.status_code == 200
    data = cash.json()
    assert data["cash_account"] is None
    assert data["recent_transactions"] == []
