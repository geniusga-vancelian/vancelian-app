"""Tests for Internal Transfer Engine v1 + hardening.

Coverage:
  1.  successful internal transfer (client → settlement)
  2.  insufficient funds
  3.  duplicate external_reference (idempotency)
  4.  ledger integrity (sum debits == sum credits)
  5.  balances updated correctly after transfer
  6.  invalid settlement account type rejected
  7.  non-master settlement rejected
  8.  client → client rejected
  9.  settlement → client rejected
  10. valid route (client → master settlement) succeeds
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import make_admin_headers, make_linked_client

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


def _admin_headers(db):
    """En-têtes acteur + JWT (wallet_transfer / beneficiary_add sur custody)."""
    return {**ADMIN_HEADERS, **make_admin_headers(db)}


def _unique_email() -> str:
    return f"transfer-{uuid.uuid4()}@example.com"


def _create_test_client(_http: TestClient, db) -> dict:
    c = make_linked_client(db, email=_unique_email())
    db.flush()
    return {"id": str(c.id), "email": c.email}


def _create_provider(http: TestClient) -> dict:
    res = http.post(
        "/api/admin/custody/providers",
        json={
            "name": f"Bank-{uuid.uuid4().hex[:6]}",
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


def _fund_client(http: TestClient, client_id: str, amount: float) -> None:
    """Simulate a deposit to fund the client account."""
    res = http.post(
        "/api/admin/custody/simulate-deposit",
        json={
            "client_id": client_id,
            "amount": amount,
            "currency": "EUR",
            "reference": f"FUND-{uuid.uuid4().hex[:8]}",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text


def _full_setup(http: TestClient, db, initial_balance: float = 1000.0):
    """Create provider + client + accounts + fund client. Returns (pe_client, client_acc, settlement_acc)."""
    pe_client = _create_test_client(http, db)
    provider = _create_provider(http)
    client_acc = _create_client_account(http, provider["id"], pe_client["id"], db)
    settlement = _create_settlement_account(http, provider["id"])
    if initial_balance > 0:
        _fund_client(http, pe_client["id"], initial_balance)
    return pe_client, client_acc, settlement


# ---------------------------------------------------------------------------
# 1. Successful internal transfer
# ---------------------------------------------------------------------------

def test_successful_internal_transfer(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 500.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert data["transaction_id"] is not None
    assert float(data["amount"]) == 500.0
    assert data["currency"] == "EUR"
    assert float(data["client_balance_after"]) == 500.0


# ---------------------------------------------------------------------------
# 2. Insufficient funds
# ---------------------------------------------------------------------------

def test_insufficient_funds(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=100.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 500.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "failed"
    assert data["error"] == "insufficient_funds"


# ---------------------------------------------------------------------------
# 3. Duplicate external_reference (idempotency)
# ---------------------------------------------------------------------------

def test_duplicate_reference(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    payload = {
        "client_account_id": client_acc["id"],
        "settlement_account_id": settlement["id"],
        "amount": 200.0,
        "currency": "EUR",
        "external_reference": ref,
    }

    res1 = client.post("/api/internal-transfer", json=payload, headers=_admin_headers(db))
    assert res1.status_code == 200
    assert res1.json()["status"] == "completed"

    res2 = client.post("/api/internal-transfer", json=payload, headers=_admin_headers(db))
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ignored"
    assert data2["reason"] == "duplicate_external_reference"


# ---------------------------------------------------------------------------
# 4. Ledger integrity (sum debits == sum credits)
# ---------------------------------------------------------------------------

def test_ledger_integrity(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 300.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200
    tx_id = res.json()["transaction_id"]

    ledger_res = client.get(
        f"/api/portfolio-engine/ledger-entries?reference_type=custody_transaction&reference_id={tx_id}",
        headers=ADMIN_HEADERS,
    )
    assert ledger_res.status_code == 200
    entries = ledger_res.json().get("items", [])
    assert len(entries) == 2

    debits = sum(float(e["amount"]) for e in entries if e["entry_type"] == "debit")
    credits_ = sum(float(e["amount"]) for e in entries if e["entry_type"] == "credit")
    assert debits == credits_ == 300.0


# ---------------------------------------------------------------------------
# 5. Balances updated correctly
# ---------------------------------------------------------------------------

def test_balances_updated(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 400.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert float(data["client_balance_after"]) == 600.0

    balances_res = client.get("/api/admin/custody/balances", headers=ADMIN_HEADERS)
    assert balances_res.status_code == 200
    all_balances = balances_res.json().get("items", [])

    client_bal = next((b for b in all_balances if b["account_id"] == client_acc["id"]), None)
    assert client_bal is not None
    assert float(client_bal["available_balance"]) == 600.0


# ---------------------------------------------------------------------------
# 6. Invalid settlement account type rejected
#    (passing a client_deposit_account as destination)
# ---------------------------------------------------------------------------

def test_invalid_settlement_account_type_rejected(client: TestClient, db):
    provider = _create_provider(client)
    pe_client_a = _create_test_client(client, db)
    pe_client_b = _create_test_client(client, db)
    client_acc_a = _create_client_account(client, provider["id"], pe_client_a["id"], db)
    client_acc_b = _create_client_account(client, provider["id"], pe_client_b["id"], db)
    _fund_client(client, pe_client_a["id"], 1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc_a["id"],
            "settlement_account_id": client_acc_b["id"],
            "amount": 100.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 400
    assert "invalid_settlement_account" in res.json()["detail"]

    # Verify no transaction was created
    txs = client.get(
        f"/api/admin/custody/transactions?account_id={client_acc_a['id']}",
        headers=ADMIN_HEADERS,
    ).json()
    xfer_txs = [t for t in txs.get("items", []) if t["transaction_type"] == "transfer_internal"]
    assert len(xfer_txs) == 0


# ---------------------------------------------------------------------------
# 7. Non-master settlement account rejected
# ---------------------------------------------------------------------------

def test_non_master_settlement_rejected(client: TestClient, db):
    """A company_settlement_account with is_master_account=false must be rejected."""
    provider = _create_provider(client)
    pe_client = _create_test_client(client, db)
    client_acc = _create_client_account(client, provider["id"], pe_client["id"], db)
    _fund_client(client, pe_client["id"], 1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": client_acc["id"],
            "amount": 50.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "invalid_settlement_account" in detail or "transfer_route_not_allowed" in detail


# ---------------------------------------------------------------------------
# 8. Client → Client transfer rejected
# ---------------------------------------------------------------------------

def test_client_to_client_transfer_rejected(client: TestClient, db):
    provider = _create_provider(client)
    pe_client_a = _create_test_client(client, db)
    pe_client_b = _create_test_client(client, db)
    acc_a = _create_client_account(client, provider["id"], pe_client_a["id"], db)
    acc_b = _create_client_account(client, provider["id"], pe_client_b["id"], db)
    _fund_client(client, pe_client_a["id"], 500.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": acc_a["id"],
            "settlement_account_id": acc_b["id"],
            "amount": 100.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 400
    assert "invalid_settlement_account" in res.json()["detail"]

    # Verify balances unchanged
    bals = client.get("/api/admin/custody/balances", headers=ADMIN_HEADERS).json()
    bal_a = next((b for b in bals["items"] if b["account_id"] == acc_a["id"]), None)
    assert bal_a is not None
    assert float(bal_a["available_balance"]) == 500.0


# ---------------------------------------------------------------------------
# 9. Settlement → Client transfer rejected
# ---------------------------------------------------------------------------

def test_settlement_to_client_transfer_rejected(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=1000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": settlement["id"],
            "settlement_account_id": client_acc["id"],
            "amount": 100.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "transfer_route_not_allowed" in detail or "invalid_settlement_account" in detail


# ---------------------------------------------------------------------------
# 10. Only valid route (client → master settlement) succeeds
# ---------------------------------------------------------------------------

def test_only_client_to_master_settlement_allowed(client: TestClient, db):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=2000.0)

    ref = f"xfer-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/internal-transfer",
        json={
            "client_account_id": client_acc["id"],
            "settlement_account_id": settlement["id"],
            "amount": 750.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=_admin_headers(db),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert float(data["client_balance_after"]) == 1250.0
