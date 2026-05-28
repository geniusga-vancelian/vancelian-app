"""Tests Phase 5B — workflow request / approve / apply contrôlé."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.discrepancy_models import (
    ReconciliationCorrection,
    ReconciliationDiscrepancy,
)
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import (
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import CHAIN_ID, _seed_wallet

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-onchain-recon-5b@example.com",
    "X-Actor-Roles": "admin",
}
ADMIN_HEADERS_B = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-onchain-recon-5b-approver@example.com",
    "X-Actor-Roles": "admin",
}
BASE = "/api/admin/onchain-reconciliation"


def _tables_ready() -> bool:
    try:
        with engine.connect() as conn:
            for table in ("reconciliation_discrepancies", "raw_onchain_events"):
                r = conn.execute(
                    sa.text(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :t"
                    ),
                    {"t": table},
                )
                if r.fetchone() is None:
                    return False
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'reconciliation_corrections' "
                    "AND column_name = 'status'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _tables_ready(),
    reason="Migrations 161+162+163 requises.",
)


def _seed_balance_only_discrepancy(
    db: Session,
    *,
    person_id: uuid.UUID,
    wallet_address: str,
    asset: str = "USDC",
    delta: Decimal = Decimal("1"),
) -> ReconciliationDiscrepancy:
    row, _ = DiscrepancyRepository.upsert_open(
        db,
        person_id=person_id,
        layer="privy",
        discrepancy_type="balance_ledger_vs_onchain",
        severity="P1",
        wallet_address=wallet_address,
        asset=asset,
        db_amount=Decimal("0"),
        onchain_amount=delta,
        delta=delta,
        metadata_json={"balance_only": True, "manual_review": True},
    )
    db.flush()
    return row


def _seed_raw_event(
    db: Session,
    *,
    wallet_address: str,
    asset: str = "USDC",
    amount_raw: int = 1_000_000,
    tx_hash: str | None = None,
) -> uuid.UUID:
    tx = tx_hash or f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    row, _ = RawOnChainEventRepository.insert_if_absent(
        db,
        data={
            "chain_id": CHAIN_ID,
            "tx_hash": tx,
            "log_index": 0,
            "wallet_address": wallet_address,
            "asset": asset,
            "amount_raw": amount_raw,
            "event_type": "erc20_transfer",
        },
    )
    db.flush()
    return row.id


def _request_approve_apply(
    client: TestClient,
    *,
    discrepancy_id: uuid.UUID,
    raw_event_id: uuid.UUID,
    approve_headers: dict | None = None,
) -> tuple[dict, dict, dict]:
    req = client.post(
        f"{BASE}/discrepancies/{discrepancy_id}/request-correction",
        headers=ADMIN_HEADERS,
        json={
            "action": "create_missing_deposit_from_raw_event",
            "raw_onchain_event_id": str(raw_event_id),
        },
    )
    assert req.status_code == 200, req.text
    correction = req.json()
    cid = correction["id"]

    appr = client.post(
        f"{BASE}/corrections/{cid}/approve",
        headers=approve_headers or ADMIN_HEADERS_B,
    )
    assert appr.status_code == 200, appr.text

    apply = client.post(
        f"{BASE}/corrections/{cid}/apply",
        headers=ADMIN_HEADERS,
    )
    assert apply.status_code == 200, apply.text
    return correction, appr.json(), apply.json()


def test_balance_only_preview_and_request_blocked(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    row = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
    )
    db.commit()

    preview = client.post(
        f"{BASE}/discrepancies/{row.id}/preview-correction",
        headers=ADMIN_HEADERS,
        json={},
    )
    assert preview.status_code == 200
    assert preview.json()["allowed_to_apply"] is False

    req = client.post(
        f"{BASE}/discrepancies/{row.id}/request-correction",
        headers=ADMIN_HEADERS,
        json={"action": "create_missing_deposit_from_raw_event"},
    )
    assert req.status_code == 400
    assert "raw" in str(req.json().get("detail", "")).lower()


def test_create_deposit_happy_path(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address)
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        delta=Decimal("1"),
    )
    db.commit()

    before_dep = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == pe.person_id).count()
    balance = PersonWalletBalanceRepository.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    before_bal = Decimal(str(balance.balance))
    db.commit()

    _, _, applied = _request_approve_apply(
        client,
        discrepancy_id=disc.id,
        raw_event_id=raw_id,
    )
    assert applied["apply_result"]["deposit_id"]

    db.expire_all()
    after_dep = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == pe.person_id).count()
    assert after_dep == before_dep + 1

    db.refresh(balance)
    assert Decimal(str(balance.balance)) == before_bal + Decimal("1")

    disc_row = db.query(ReconciliationDiscrepancy).filter(ReconciliationDiscrepancy.id == disc.id).first()
    assert disc_row.status == "resolved"


def test_double_apply_idempotent(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address)
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
    )
    db.commit()

    correction, _, _ = _request_approve_apply(
        client,
        discrepancy_id=disc.id,
        raw_event_id=raw_id,
    )
    cid = correction["id"]

    second = client.post(f"{BASE}/corrections/{cid}/apply", headers=ADMIN_HEADERS)
    assert second.status_code == 400

    dep_count = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == pe.person_id).count()
    assert dep_count == 1


def test_same_approver_production_refused(client: TestClient, db: Session, monkeypatch):
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

    monkeypatch.setattr(
        "services.onchain_reconciliation.correction_policy.is_production_env",
        lambda: True,
    )
    appr = client.post(f"{BASE}/corrections/{cid}/approve", headers=ADMIN_HEADERS)
    assert appr.status_code == 400
    assert "production" in str(appr.json().get("detail", "")).lower()


def test_same_approver_dev_without_flag_refused(client: TestClient, db: Session, monkeypatch):
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
    cid = req.json()["id"]

    monkeypatch.delenv("ONCHAIN_RECONCILIATION_ALLOW_SINGLE_APPROVER_DEV", raising=False)
    monkeypatch.setattr(
        "services.onchain_reconciliation.correction_policy.is_production_env",
        lambda: False,
    )
    monkeypatch.setattr(
        "services.onchain_reconciliation.correction_policy.allow_single_approver_dev",
        lambda: False,
    )
    appr = client.post(f"{BASE}/corrections/{cid}/approve", headers=ADMIN_HEADERS)
    assert appr.status_code == 400


def test_same_approver_dev_with_flag_allowed(client: TestClient, db: Session, monkeypatch):
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
    cid = req.json()["id"]

    monkeypatch.setenv("ONCHAIN_RECONCILIATION_ALLOW_SINGLE_APPROVER_DEV", "true")
    monkeypatch.setattr(
        "services.onchain_reconciliation.correction_policy.is_production_env",
        lambda: False,
    )
    appr = client.post(f"{BASE}/corrections/{cid}/approve", headers=ADMIN_HEADERS)
    assert appr.status_code == 200


def test_asset_mismatch_refused(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address, asset="EURC")
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        asset="USDC",
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
    assert req.status_code == 400
    assert "asset" in str(req.json().get("detail", "")).lower()


def test_wallet_mismatch_refused(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    other = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=other.address)
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
    assert req.status_code == 400
    assert "wallet" in str(req.json().get("detail", "")).lower()


def test_amount_exceeds_delta_refused(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    raw_id = _seed_raw_event(db, wallet_address=wallet.address, amount_raw=5_000_000)
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        delta=Decimal("1"),
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
    assert req.status_code == 400
    assert "amount" in str(req.json().get("detail", "")).lower()


def test_non_whitelisted_action_refused(client: TestClient, db: Session):
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
            "action": "void_deposit",
            "raw_onchain_event_id": str(raw_id),
        },
    )
    assert req.status_code == 400
    assert "whitelist" in str(req.json().get("detail", "")).lower()


def test_ignore_no_balance_change(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    disc = _seed_balance_only_discrepancy(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
    )
    db.commit()

    def _fail(*args, **kwargs):
        raise AssertionError("balance mutation forbidden")

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", _fail)

    res = client.post(
        f"{BASE}/discrepancies/{disc.id}/ignore",
        headers=ADMIN_HEADERS,
        json={},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
