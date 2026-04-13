"""Tests for Custody Hardening & BAS Webhook Engine v1.

Coverage:
  1.  duplicate webhook ignored (same ref + same payload)
  2.  same external_reference different payload -> failed (not processed)
  3.  out-of-order event rejected by state machine
  4.  currency mismatch rejected
  5.  unknown IBAN/account rejected
  6.  reversal transaction
  7.  concurrent withdraw (optimistic lock)
  8.  webhook replay via admin endpoint
  9.  unique constraint (provider_id, external_reference) on transactions
  10. state machine validates transitions
  11. balance version increments on update
  12. currency validation strict on deposit
  13. ledger double-entry invariant after webhook deposit
  14. withdrawal_completed via webhook flow
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


def _admin_headers(db):
    return {**ADMIN_HEADERS, **make_admin_headers(db)}


def _unique_email() -> str:
    return f"hardening-{uuid.uuid4()}@example.com"


def _create_test_client(_http: TestClient, db) -> dict:
    from tests.conftest import make_linked_client

    c = make_linked_client(db, email=_unique_email())
    db.flush()
    return {"id": str(c.id), "email": c.email}


def _create_provider(http: TestClient, name=None) -> dict:
    res = http.post(
        "/api/admin/custody/providers",
        json={
            "name": name or f"Bank-{uuid.uuid4().hex[:6]}",
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
    pe_client = _create_test_client(http, db)
    provider = _create_provider(http)
    client_acc = _create_client_account(http, provider["id"], pe_client["id"], db)
    settlement = _create_settlement_account(http, provider["id"])
    return provider, pe_client, client_acc, settlement


def _send_webhook(http: TestClient, provider_name: str, payload: dict):
    return http.post(
        f"/api/webhooks/custody/{provider_name}",
        json=payload,
    )


# ---------------------------------------------------------------------------
# 1. Duplicate webhook ignored (same ref + same payload)
# ---------------------------------------------------------------------------

def test_duplicate_webhook_ignored(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    # Seed balance via simulation
    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )

    payload = {
        "event_type": "deposit",
        "reference": "DEPOSIT-DUP-001",
        "iban": client_acc["iban"],
        "amount": 1000,
        "currency": "EUR",
    }

    r1 = _send_webhook(client, provider["name"], payload)
    assert r1.status_code == 200
    assert r1.json()["processing_status"] == "processed"

    r2 = _send_webhook(client, provider["name"], payload)
    assert r2.status_code == 200
    assert r2.json()["processing_status"] == "duplicate"


# ---------------------------------------------------------------------------
# 2. Same external_reference, different payload -> failed
# ---------------------------------------------------------------------------

def test_same_ref_different_payload_is_failed(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 5000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )

    payload_a = {
        "event_type": "deposit",
        "reference": "CONFLICT-REF-001",
        "iban": client_acc["iban"],
        "amount": 1000,
        "currency": "EUR",
    }
    r1 = _send_webhook(client, provider["name"], payload_a)
    assert r1.status_code == 200
    assert r1.json()["processing_status"] == "processed"

    payload_b = {
        "event_type": "deposit",
        "reference": "CONFLICT-REF-001",
        "iban": client_acc["iban"],
        "amount": 2000,
        "currency": "EUR",
    }
    r2 = _send_webhook(client, provider["name"], payload_b)
    assert r2.status_code == 200
    status = r2.json()["processing_status"]
    assert status == "failed", f"Expected 'failed', got '{status}'"


# ---------------------------------------------------------------------------
# 3. Out-of-order event rejected by state machine
# ---------------------------------------------------------------------------

def test_out_of_order_event_rejected(client: TestClient):
    from services.custody.state_machine import InvalidTransitionError, validate_transition

    with pytest.raises(InvalidTransitionError):
        validate_transition("completed", "processing")

    with pytest.raises(InvalidTransitionError):
        validate_transition("failed", "completed")

    with pytest.raises(InvalidTransitionError):
        validate_transition("reversed", "completed")


# ---------------------------------------------------------------------------
# 4. Currency mismatch rejected
# ---------------------------------------------------------------------------

def test_currency_mismatch(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    payload = {
        "event_type": "deposit",
        "reference": f"CURR-MISMATCH-{uuid.uuid4().hex[:6]}",
        "iban": client_acc["iban"],
        "amount": 500,
        "currency": "USD",
    }
    r = _send_webhook(client, provider["name"], payload)
    assert r.status_code == 200
    assert r.json()["processing_status"] == "failed"


# ---------------------------------------------------------------------------
# 5. Unknown IBAN/account rejected
# ---------------------------------------------------------------------------

def test_unknown_account(client: TestClient, db):
    provider, _, _, _ = _full_setup(client, db)

    payload = {
        "event_type": "deposit",
        "reference": f"UNKNOWN-{uuid.uuid4().hex[:6]}",
        "iban": "DE00000000000000000",
        "amount": 500,
        "currency": "EUR",
    }
    r = _send_webhook(client, provider["name"], payload)
    assert r.status_code == 200
    assert r.json()["processing_status"] == "failed"


# ---------------------------------------------------------------------------
# 6. Reversal transaction
# ---------------------------------------------------------------------------

def test_reversal_transaction(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    deposit_payload = {
        "event_type": "deposit",
        "reference": f"REV-ORIG-{uuid.uuid4().hex[:6]}",
        "iban": client_acc["iban"],
        "amount": 3000,
        "currency": "EUR",
    }
    r1 = _send_webhook(client, provider["name"], deposit_payload)
    assert r1.status_code == 200
    assert r1.json()["processing_status"] == "processed"

    reversal_payload = {
        "event_type": "reversal",
        "reference": f"REV-NEW-{uuid.uuid4().hex[:6]}",
        "original_reference": deposit_payload["reference"],
        "iban": client_acc["iban"],
        "amount": 3000,
        "currency": "EUR",
    }
    r2 = _send_webhook(client, provider["name"], reversal_payload)
    assert r2.status_code == 200
    assert r2.json()["processing_status"] == "processed"

    txs = client.get("/api/admin/custody/transactions", headers=ADMIN_HEADERS).json()
    reversal_found = False
    for t in txs.get("items", []):
        if t.get("reversal_of_transaction_id"):
            reversal_found = True
            break
    assert reversal_found, "Expected a reversal transaction"


# ---------------------------------------------------------------------------
# 7. Concurrent withdraw (optimistic lock)
# ---------------------------------------------------------------------------

def test_concurrent_withdraw_optimistic_lock(client: TestClient, db):
    from services.custody.repository import CustodyBalanceRepository, OptimisticLockError
    from decimal import Decimal

    _, pe_client, client_acc, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 10000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )

    balance = CustodyBalanceRepository.get_by_account_id(db, uuid.UUID(client_acc["id"]))
    assert balance is not None

    old_version = balance.version
    CustodyBalanceRepository.update_balance(
        db, balance, delta=Decimal("-1000"), expected_version=old_version
    )
    db.flush()

    with pytest.raises(OptimisticLockError):
        CustodyBalanceRepository.update_balance(
            db, balance, delta=Decimal("-1000"), expected_version=old_version
        )


# ---------------------------------------------------------------------------
# 8. Webhook replay via admin endpoint
# ---------------------------------------------------------------------------

def test_webhook_replay(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    payload = {
        "event_type": "deposit",
        "reference": f"REPLAY-{uuid.uuid4().hex[:6]}",
        "iban": client_acc["iban"],
        "amount": 500,
        "currency": "EUR",
    }
    r1 = _send_webhook(client, provider["name"], payload)
    assert r1.status_code == 200
    event_id = r1.json()["event_id"]

    r2 = client.post(
        f"/api/admin/custody/webhook-events/{event_id}/replay",
        headers=_admin_headers(db),
    )
    assert r2.status_code == 200
    assert r2.json()["processing_status"] in ("processed", "duplicate")


# ---------------------------------------------------------------------------
# 9. Unique constraint (provider_id, external_reference) on transactions
# ---------------------------------------------------------------------------

def test_unique_constraint_provider_extref(client: TestClient, db):
    """Sending the same webhook twice should NOT create two custody_transactions."""
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    ref = f"UNIQUE-{uuid.uuid4().hex[:6]}"
    payload = {
        "event_type": "deposit",
        "reference": ref,
        "iban": client_acc["iban"],
        "amount": 750,
        "currency": "EUR",
    }

    _send_webhook(client, provider["name"], payload)
    _send_webhook(client, provider["name"], payload)

    txs = client.get("/api/admin/custody/transactions", headers=ADMIN_HEADERS).json()
    matches = [t for t in txs.get("items", []) if t.get("external_reference") == ref]
    assert len(matches) == 1, f"Expected exactly 1 tx for ref {ref}, got {len(matches)}"


# ---------------------------------------------------------------------------
# 10. State machine validates transitions
# ---------------------------------------------------------------------------

def test_state_machine_valid_transitions(client: TestClient):
    from services.custody.state_machine import validate_transition, InvalidTransitionError

    validate_transition("pending", "processing")
    validate_transition("processing", "completed")
    validate_transition("processing", "failed")
    validate_transition("completed", "reversed")
    validate_transition("pending", "failed")

    for bad in [
        ("completed", "processing"),
        ("failed", "completed"),
        ("reversed", "completed"),
        ("reversed", "pending"),
        ("failed", "processing"),
    ]:
        with pytest.raises(InvalidTransitionError):
            validate_transition(bad[0], bad[1])


# ---------------------------------------------------------------------------
# 11. Balance version increments on update
# ---------------------------------------------------------------------------

def test_balance_version_increments(client: TestClient, db):
    _, pe_client, _, _ = _full_setup(client, db)

    from services.custody.repository import CustodyBalanceRepository, CustodyAccountRepository
    from decimal import Decimal

    acc = CustodyAccountRepository.find_client_account(
        db, uuid.UUID(pe_client["id"]), "EUR"
    )
    assert acc is not None, "Client EUR account should exist"
    balance = CustodyBalanceRepository.get_by_account_id(db, acc.id)
    assert balance is not None

    v1 = balance.version
    CustodyBalanceRepository.update_balance(db, balance, delta=Decimal("100"))
    db.flush()
    assert balance.version == v1 + 1

    CustodyBalanceRepository.update_balance(db, balance, delta=Decimal("200"))
    db.flush()
    assert balance.version == v1 + 2


# ---------------------------------------------------------------------------
# 12. Currency validation strict on deposit simulation
# ---------------------------------------------------------------------------

def test_currency_validation_strict_on_simulate(client: TestClient, db):
    """Deposit simulation on a EUR account with USD should fail (CurrencyMismatchError or 404)."""
    _, pe_client, _, _ = _full_setup(client, db)

    res = client.post(
        "/api/admin/custody/simulate-deposit",
        json={
            "client_id": pe_client["id"],
            "amount": 1000,
            "currency": "USD",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code in (400, 404), f"Expected 400/404, got {res.status_code}"


# ---------------------------------------------------------------------------
# 13. Ledger double-entry invariant after webhook deposit
# ---------------------------------------------------------------------------

def test_ledger_invariant_after_webhook_deposit(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    payload = {
        "event_type": "deposit",
        "reference": f"LEDGER-INV-{uuid.uuid4().hex[:6]}",
        "iban": client_acc["iban"],
        "amount": 2500,
        "currency": "EUR",
    }
    r = _send_webhook(client, provider["name"], payload)
    assert r.status_code == 200
    assert r.json()["processing_status"] == "processed"

    from services.portfolio_engine.ledger_entries.models import LedgerEntry

    entries = db.query(LedgerEntry).filter(
        LedgerEntry.reference_type == "custody_transaction"
    ).all()

    total_debit = sum(float(e.amount) for e in entries if e.entry_type == "debit")
    total_credit = sum(float(e.amount) for e in entries if e.entry_type == "credit")
    assert abs(total_debit - total_credit) < 0.01, (
        f"Ledger invariant broken: debits={total_debit}, credits={total_credit}"
    )


# ---------------------------------------------------------------------------
# 14. Withdrawal completed via webhook flow
# ---------------------------------------------------------------------------

def test_withdrawal_completed_via_webhook(client: TestClient, db):
    provider, pe_client, client_acc, _ = _full_setup(client, db)

    client.post(
        "/api/admin/custody/simulate-deposit",
        json={"client_id": pe_client["id"], "amount": 10000, "currency": "EUR"},
        headers=ADMIN_HEADERS,
    )

    req_ref = f"WD-REQ-{uuid.uuid4().hex[:6]}"
    req_payload = {
        "event_type": "withdrawal_requested",
        "reference": req_ref,
        "iban": client_acc["iban"],
        "amount": 2000,
        "currency": "EUR",
    }
    r1 = _send_webhook(client, provider["name"], req_payload)
    assert r1.status_code == 200
    assert r1.json()["processing_status"] == "processed"

    comp_payload = {
        "event_type": "withdrawal_completed",
        "reference": f"WD-COMP-{uuid.uuid4().hex[:6]}",
        "original_reference": req_ref,
        "iban": client_acc["iban"],
        "amount": 2000,
        "currency": "EUR",
    }
    r2 = _send_webhook(client, provider["name"], comp_payload)
    assert r2.status_code == 200
    assert r2.json()["processing_status"] == "processed"
