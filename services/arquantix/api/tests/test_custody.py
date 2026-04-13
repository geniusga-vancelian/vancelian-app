"""Tests for Custody Fiat Foundation v1.

Coverage:
  1.  create provider
  2.  create client deposit account
  3.  create settlement account
  4.  list accounts
  5.  simulate deposit
  6.  simulate withdrawal
  7.  balance update after operations
  8.  withdraw with insufficient funds
  9.  ledger entries created (invariant check)
  10. admin RBAC (client/advisor forbidden)
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_admin_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}

CLIENT_HEADERS = {
    "X-Actor-Type": "client",
    "X-Actor-Id": "some-client",
    "X-Actor-Roles": "client",
}

ADVISOR_HEADERS = {
    "X-Actor-Type": "advisor",
    "X-Actor-Id": "some-advisor",
    "X-Actor-Roles": "advisor",
}


def _admin_headers(db):
    """Headers admin custody + JWT (requis pour actions sensibles : retrait, bénéficiaire)."""
    return {**ADMIN_HEADERS, **make_admin_headers(db)}


def _unique_email() -> str:
    return f"custody-{uuid.uuid4()}@example.com"


def _create_test_client(_http: TestClient, db) -> dict:
    """Crée un client PE en ORM (insert direct) pour préserver la session du test."""
    from tests.conftest import make_linked_client

    c = make_linked_client(db, email=_unique_email())
    db.flush()
    return {"id": str(c.id), "email": c.email}


def _create_provider(http: TestClient, name: str = "TestBank") -> dict:
    res = http.post(
        "/api/admin/custody/providers",
        json={
            "name": name,
            "provider_type": "bank",
            "jurisdiction": "EU",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_client_account(http: TestClient, provider_id: str, client_id: str, db) -> dict:
    res = http.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider_id,
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "Test User",
            "client_id": client_id,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_settlement_account(http: TestClient, provider_id: str) -> dict:
    res = http.post(
        "/api/admin/custody/accounts/settlement",
        json={
            "provider_id": provider_id,
            "account_type": "company_settlement_account",
            "currency": "EUR",
            "account_holder_name": "Vancelian SA",
            "is_master_account": True,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=ADMIN_HEADERS,
    )
    if res.status_code == 409:
        accs = http.get(
            "/api/admin/custody/accounts?account_type=company_settlement_account",
            headers=ADMIN_HEADERS,
        ).json()
        for a in accs.get("items", []):
            if a["is_master_account"] and a["currency"] == "EUR":
                return a
    assert res.status_code == 201, res.text
    return res.json()


def _full_setup(http: TestClient, db):
    """Create provider + client + client account + settlement account. Returns (provider, pe_client, client_account, settlement_account)."""
    pe_client = _create_test_client(http, db)
    provider = _create_provider(http, f"Bank-{uuid.uuid4().hex[:6]}")
    client_acc = _create_client_account(http, provider["id"], pe_client["id"], db)
    settlement = _create_settlement_account(http, provider["id"])
    return provider, pe_client, client_acc, settlement


# ---------------------------------------------------------------------------
# 1. Create provider
# ---------------------------------------------------------------------------

def test_create_provider(client: TestClient):
    data = _create_provider(client, "Modular")
    assert data["name"] == "Modular"
    assert data["provider_type"] == "bank"
    assert data["jurisdiction"] == "EU"
    assert data["status"] == "active"


# ---------------------------------------------------------------------------
# 2. Create client deposit account
# ---------------------------------------------------------------------------

def test_create_client_account(client: TestClient, db):
    pe_client = _create_test_client(client, db)
    provider = _create_provider(client)
    acc = _create_client_account(client, provider["id"], pe_client["id"], db)

    assert acc["account_type"] == "client_deposit_account"
    assert acc["client_id"] == pe_client["id"]
    assert acc["is_master_account"] is False
    assert acc["status"] == "active"
    assert acc["available_balance"] is not None


# ---------------------------------------------------------------------------
# 3. Create settlement account
# ---------------------------------------------------------------------------

def test_create_settlement_account(client: TestClient):
    provider = _create_provider(client)
    acc = _create_settlement_account(client, provider["id"])

    assert acc["account_type"] == "company_settlement_account"
    assert acc["is_master_account"] is True
    assert acc["client_id"] is None


# ---------------------------------------------------------------------------
# 4. List accounts
# ---------------------------------------------------------------------------

def test_list_accounts(client: TestClient, db):
    _full_setup(client, db)

    res = client.get("/api/admin/custody/accounts", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert data["total"] >= 2


# ---------------------------------------------------------------------------
# 5. Simulate deposit
# ---------------------------------------------------------------------------

def test_simulate_deposit(client: TestClient, db):
    _, pe_client, _, _ = _full_setup(client, db)

    res = client.post(
        "/api/admin/custody/simulate-deposit",
        json={
            "client_id": pe_client["id"],
            "amount": 1000.00,
            "currency": "EUR",
            "reference": "DEP-001",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["direction"] == "credit"
    assert float(data["amount"]) == 1000.00
    assert float(data["new_available_balance"]) == 1000.00


# ---------------------------------------------------------------------------
# 6. Simulate withdrawal
# ---------------------------------------------------------------------------

def test_simulate_withdrawal(client: TestClient, db):
    _, pe_client, _, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )

    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={
            "client_id": pe_client["id"],
            "amount": 2000.00,
            "currency": "EUR",
            "reference": "WTH-001",
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["direction"] == "debit"
    assert float(data["amount"]) == 2000.00
    assert float(data["new_available_balance"]) == 3000.00


# ---------------------------------------------------------------------------
# 7. Balance update after operations
# ---------------------------------------------------------------------------

def test_balance_update_after_operations(client: TestClient, db):
    _, pe_client, _, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 10000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 3000, "currency": "EUR"},
        headers=_admin_headers(db),
    )

    res = client.get("/api/admin/custody/balances", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1


# ---------------------------------------------------------------------------
# 8. Withdraw with insufficient funds
# ---------------------------------------------------------------------------

def test_withdraw_insufficient_funds(client: TestClient, db):
    _, pe_client, _, _ = _full_setup(client, db)

    res = client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={
            "client_id": pe_client["id"],
            "amount": 999999.00,
            "currency": "EUR",
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 400, res.text
    data = res.json()
    assert "Insufficient" in data["detail"]


# ---------------------------------------------------------------------------
# 9. Ledger entries created (invariant check)
# ---------------------------------------------------------------------------

def test_ledger_entries_created(client: TestClient, db):
    """After deposit + withdrawal, verify ledger entries exist and sum(debits) == sum(credits)."""
    _, pe_client, _, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )
    client.post(
        "/api/admin/custody/simulate-withdrawal",
        json={"client_id": pe_client["id"], "amount": 1500, "currency": "EUR"},
        headers=_admin_headers(db),
    )

    from services.portfolio_engine.ledger_entries.models import LedgerEntry

    entries = db.query(LedgerEntry).filter(
        LedgerEntry.reference_type == "custody_transaction"
    ).all()

    assert len(entries) >= 4, f"Expected at least 4 ledger entries, got {len(entries)}"

    total_debit = sum(float(e.amount) for e in entries if e.entry_type == "debit")
    total_credit = sum(float(e.amount) for e in entries if e.entry_type == "credit")
    assert abs(total_debit - total_credit) < 0.01, (
        f"Ledger invariant broken: debits={total_debit}, credits={total_credit}"
    )


# ---------------------------------------------------------------------------
# 10. Admin RBAC (client/advisor forbidden)
# ---------------------------------------------------------------------------

def test_custody_admin_rbac(client: TestClient):
    res_client = client.get("/api/admin/custody/providers", headers=CLIENT_HEADERS)
    assert res_client.status_code == 403

    res_advisor = client.get("/api/admin/custody/providers", headers=ADVISOR_HEADERS)
    assert res_advisor.status_code == 403

    res_admin = client.get("/api/admin/custody/providers", headers=ADMIN_HEADERS)
    assert res_admin.status_code == 200
