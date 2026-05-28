"""Tests admin Phase 5A — discrepancies workflow sans modification balances."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.privy_wallet.repository import PersonWalletBalanceRepository
from tests.conftest import make_linked_client

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-onchain-recon-admin@example.com",
    "X-Actor-Roles": "admin",
}
CLIENT_HEADERS = {
    "X-Actor-Type": "user",
    "X-Actor-Id": "test-user@example.com",
    "X-Actor-Roles": "client",
}

BASE = "/api/admin/onchain-reconciliation/discrepancies"


def _migration_162_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'reconciliation_discrepancies'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_162_applied(),
    reason="Migration 162 requise.",
)


def _seed_discrepancy(db: Session, person_id: uuid.UUID) -> ReconciliationDiscrepancy:
    row, _ = DiscrepancyRepository.upsert_open(
        db,
        person_id=person_id,
        layer="privy",
        discrepancy_type="admin_sim_deposit",
        severity="P1",
        wallet_address="0x" + uuid.uuid4().hex[:40],
        asset="USDC",
        db_amount=Decimal("10"),
        onchain_amount=Decimal("0"),
        delta=Decimal("10"),
        reference_type="deposit",
        reference_id=f"admin_sim_{uuid.uuid4().hex[:8]}",
        metadata_json={"idempotency_key": "admin_sim_test"},
    )
    db.flush()
    return row


def test_list_discrepancies_requires_admin(client: TestClient, db: Session):
    pe = make_linked_client(db)
    _seed_discrepancy(db, pe.person_id)
    db.commit()

    denied = client.get(BASE, headers=CLIENT_HEADERS)
    assert denied.status_code == 403

    res = client.get(
        f"{BASE}?person_id={pe.person_id}&status=open&layer=privy",
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(i["person_id"] == str(pe.person_id) for i in body["items"])


def test_acknowledge_changes_status_only(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    row = _seed_discrepancy(db, pe.person_id)
    db.commit()

    def _fail_balance(*args, **kwargs):
        raise AssertionError("balance mutation forbidden")

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", _fail_balance)

    res = client.post(
        f"{BASE}/{row.id}/acknowledge",
        headers=ADMIN_HEADERS,
        json={"note": "vu en revue"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "acknowledged"


def test_ignore_changes_status_only(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    row = _seed_discrepancy(db, pe.person_id)
    db.commit()

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())

    res = client.post(
        f"{BASE}/{row.id}/ignore",
        headers=ADMIN_HEADERS,
        json={},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ignored"
    assert data["resolved_at"] is not None


def test_resolve_manually_metadata_and_status_only(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    row = _seed_discrepancy(db, pe.person_id)
    db.commit()

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())

    res = client.post(
        f"{BASE}/{row.id}/resolve-manually",
        headers=ADMIN_HEADERS,
        json={
            "note": "Qualifié manuellement — pas de correction auto",
            "resolution_code": "manual_review",
            "metadata_json": {"reviewer": "ops"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "resolved"
    assert data["metadata_json"]["resolution_note"] == "Qualifié manuellement — pas de correction auto"


def test_preview_correction_dry_run_no_balance_change(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    row = _seed_discrepancy(db, pe.person_id)
    db.commit()

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())

    res = client.post(
        f"{BASE}/{row.id}/preview-correction",
        headers=ADMIN_HEADERS,
        json={},
    )
    assert res.status_code == 200
    preview = res.json()
    assert preview["allowed_to_apply"] is False
    assert preview["dry_run"] is True
    assert preview["action"] == "mark_admin_sim_as_phantom_candidate"
    assert preview["correction_id"]
    assert preview["requires_second_approval"] is True
