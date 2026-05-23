"""Tests synchronisation wallets Privy."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import PersonExternalIdentity, engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person
from services.privy_wallet.wallet_sync import (
    normalize_privy_wallet_payload,
    reconcile_person_privy_wallets,
    sync_wallets_from_privy_linked_accounts,
)
from tests.conftest import make_linked_client


def _migration_158_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'person_crypto_wallets'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_158_applied(),
    reason="Appliquer alembic 158 pour person_crypto_wallets.",
)


def test_normalize_privy_wallet_payload_ethereum():
    item = normalize_privy_wallet_payload(
        {
            "type": "wallet",
            "address": "0x7ae683c429ec2bc66bf1eb93713b5644dd265a44",
            "chain_type": "ethereum",
            "chain_id": "eip155:1",
            "connector_type": "embedded",
        }
    )
    assert item is not None
    assert item.chain_type == "evm"
    assert item.chain_id == 1
    assert item.wallet_type == "embedded"


def _evm_address() -> str:
    return f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"


def test_sync_wallets_from_linked_accounts(db: Session):
    pe = make_linked_client(db)
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:{uuid.uuid4().hex[:12]}",
        external_email=pe.email,
    )
    db.flush()

    result = sync_wallets_from_privy_linked_accounts(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        linked_accounts=[
            {
                "type": "wallet",
                "address": _evm_address(),
                "chain_type": "ethereum",
                "chain_id": 1,
                "connector_type": "embedded",
            }
        ],
        source="test",
    )
    assert result.synced_count == 1
    assert result.wallets[0]["address"].startswith("0x")


def test_admin_reconcile_manual_address(client: TestClient, db: Session):
    pe = make_linked_client(db)
    privy_uid = f"did:privy:{uuid.uuid4().hex[:12]}"
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=privy_uid,
        external_email=pe.email,
    )
    db.commit()

    addr = _evm_address()
    res = client.post(
        "/api/admin/privy-wallet/reconcile-wallets",
        json={"person_id": str(pe.person_id), "manual_address": addr},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["synced_count"] == 1
    assert body["source"] == "manual_address"
    assert body["wallets"][0]["address"].lower() == addr.lower()
