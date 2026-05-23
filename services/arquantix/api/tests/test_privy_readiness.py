"""Tests readiness Privy — infra + client."""
from __future__ import annotations

from tests.conftest import make_linked_client


def test_infra_readiness_local(client, db, monkeypatch):
    monkeypatch.setenv("PRIVY_APP_ID", "test-app-id")
    monkeypatch.setenv("PRIVY_JWKS_URL", "https://example.com/jwks.json")
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "jwt")
    monkeypatch.setenv("PRIVY_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("PRIVY_APP_SECRET", "secret-test")

    res = client.get(
        "/api/admin/privy-wallet/infra-readiness",
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["exchange"]["ready"] is True
    assert body["webhook"]["secret_configured"] is True
    assert body["reconcile_api"]["ready"] is True
    assert body["ledger_schema"]["migration_158_applied"] is True


def test_customer_readiness_linked_wallet(client, db):
    from services.auth.person_identity_bridge import link_external_identity_to_person
    from tests.test_privy_wallet_deposits import _seed_privy_wallet

    pe = make_linked_client(db)
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider="privy",
        external_subject=f"did:privy:test_{pe.person_id.hex[:8]}",
        external_email=pe.email,
    )
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    res = client.get(
        f"/api/admin/privy-wallet/customer-readiness/{pe.person_id}",
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["primary_wallet"]["address"].lower() == wallet.address.lower()
    by_key = {c["key"]: c for c in body["checks"]}
    assert by_key["privy_identity_linked"]["ok"] is True
    assert by_key["active_wallet"]["ok"] is True
