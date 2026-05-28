"""Tests Phase 5C — durcissement apply + consommation raw event."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import RawOnChainEvent
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import CHAIN_ID, _seed_wallet
from tests.test_phase5b_correction_workflow import (
    ADMIN_HEADERS,
    ADMIN_HEADERS_B,
    BASE,
    _request_approve_apply,
    _seed_balance_only_discrepancy,
    _seed_raw_event,
)


def _migration_164_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'raw_onchain_events' "
                    "AND column_name = 'consumed_by_correction_id'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_164_ready(),
    reason="Migration 164 requise.",
)


def test_apply_refused_when_discrepancy_resolved(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address)
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
    )
    db.commit()

    req = client.post(
        f"{BASE}/discrepancies/{disc.id}/request-correction",
        headers=ADMIN_HEADERS,
        json={
            "action": "create_missing_deposit_from_raw_event",
            "raw_onchain_event_id": str(raw_id),
        },
    )
    assert req.status_code == 200
    cid = req.json()["id"]
    appr = client.post(f"{BASE}/corrections/{cid}/approve", headers=ADMIN_HEADERS_B)
    assert appr.status_code == 200

    disc_row = DiscrepancyRepository.find_by_id(db, disc.id)
    DiscrepancyRepository.update_status(db, disc_row, status="resolved", resolved=True)
    db.commit()

    apply = client.post(f"{BASE}/corrections/{cid}/apply", headers=ADMIN_HEADERS)
    assert apply.status_code == 400
    assert "discrepancy_status" in str(apply.json().get("detail", "")).lower()


def test_second_discrepancy_cannot_consume_same_raw_event(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address)
    disc1 = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        delta=Decimal("1"),
    )
    disc2, _ = DiscrepancyRepository.upsert_open(
        db,
        person_id=pe.person_id,
        layer="privy",
        discrepancy_type="balance_ledger_vs_onchain",
        severity="P1",
        wallet_address=wallet.address,
        asset="USDC",
        db_amount=Decimal("0"),
        onchain_amount=Decimal("2"),
        delta=Decimal("2"),
        reference_type="balance",
        reference_id=f"bal2_{uuid.uuid4().hex[:8]}",
    )
    db.commit()

    _request_approve_apply(client, discrepancy_id=disc1.id, raw_event_id=raw_id)

    req2 = client.post(
        f"{BASE}/discrepancies/{disc2.id}/request-correction",
        headers=ADMIN_HEADERS,
        json={
            "action": "create_missing_deposit_from_raw_event",
            "raw_onchain_event_id": str(raw_id),
        },
    )
    assert req2.status_code == 400
    assert "consumed" in str(req2.json().get("detail", "")).lower()

    raw_row = db.query(RawOnChainEvent).filter(RawOnChainEvent.id == raw_id).first()
    assert raw_row.consumed_by_correction_id is not None


def test_export_csv_audit(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
    )
    db.commit()

    res = client.get(f"{BASE}/export.csv?export_type=audit&limit=100", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    body = res.text
    assert "discrepancy_type" in body
    assert "requested_by" in body
