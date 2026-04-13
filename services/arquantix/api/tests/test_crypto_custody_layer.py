"""Tests for crypto custody layer: accounts, balances, bootstrap, settlement uses DB."""
from __future__ import annotations

from datetime import date

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import SessionLocal
from services.exchange.assets import SUPPORTED_ASSETS, clear_settlement_wallet_balances, set_settlement_wallet_balance
from services.exchange.custody_repository import (
    ACCOUNT_TYPE_CLIENTS_POOL,
    ACCOUNT_TYPE_SETTLEMENT_WALLET,
    CryptoCustodyAccountRepository,
    CryptoCustodyBalanceRepository,
)

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


def test_bootstrap_creates_two_accounts_per_asset(client: TestClient):
    """POST /api/admin/exchange/crypto-custody/bootstrap creates clients_pool + settlement_wallet per asset."""
    res = client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"
    created = data["created"]
    assert data["count"] == len(SUPPORTED_ASSETS) * 2
    types_per_asset = {}
    for item in created:
        asset = item["asset"]
        types_per_asset.setdefault(asset, set()).add(item["account_type"])
    for asset in SUPPORTED_ASSETS:
        assert ACCOUNT_TYPE_CLIENTS_POOL in types_per_asset.get(asset, set())
        assert ACCOUNT_TYPE_SETTLEMENT_WALLET in types_per_asset.get(asset, set())


def test_bootstrap_idempotent(client: TestClient):
    """Second bootstrap returns same accounts (get_or_create)."""
    res1 = client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    assert res1.status_code == 200
    res2 = client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    assert res2.status_code == 200
    assert res1.json()["count"] == res2.json()["count"]


def test_custody_accounts_unique_asset_type(db: Session):
    """Uniqueness (asset, account_type) is enforced."""
    acc = CryptoCustodyAccountRepository.get_or_create_account(db, "BTC", ACCOUNT_TYPE_CLIENTS_POOL)
    assert acc.id is not None
    acc2 = CryptoCustodyAccountRepository.get_or_create_account(db, "BTC", ACCOUNT_TYPE_CLIENTS_POOL)
    assert acc.id == acc2.id


def test_get_or_create_balance(db: Session):
    """get_or_create_balance creates balance row for account; second call returns same row (idempotent)."""
    acc = CryptoCustodyAccountRepository.get_or_create_account(db, "ETH", ACCOUNT_TYPE_SETTLEMENT_WALLET)
    bal = CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, "ETH")
    assert bal.account_id == acc.id
    assert bal.asset == "ETH"
    bal2 = CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, "ETH")
    assert bal.id == bal2.id


def test_update_actual_balance(db: Session):
    """update_actual_balance sets actual_balance."""
    acc = CryptoCustodyAccountRepository.get_or_create_account(db, "BTC", ACCOUNT_TYPE_SETTLEMENT_WALLET)
    CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, "BTC")
    CryptoCustodyBalanceRepository.update_actual_balance(db, acc.id, Decimal("1.5"), provider_timestamp=None)
    bal = CryptoCustodyBalanceRepository.get_balance(db, acc.id)
    assert bal is not None
    assert Decimal(str(bal.actual_balance)) == Decimal("1.5")


def test_update_expected_balance(db: Session):
    """update_expected_balance supports delta and absolute."""
    acc = CryptoCustodyAccountRepository.get_or_create_account(db, "BTC", ACCOUNT_TYPE_CLIENTS_POOL)
    CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, "BTC")
    CryptoCustodyBalanceRepository.update_expected_balance(db, acc.id, absolute=Decimal("2.0"))
    bal = CryptoCustodyBalanceRepository.get_balance(db, acc.id)
    assert Decimal(str(bal.expected_balance)) == Decimal("2.0")
    CryptoCustodyBalanceRepository.update_expected_balance(db, acc.id, amount_delta=Decimal("0.5"))
    bal = CryptoCustodyBalanceRepository.get_balance(db, acc.id)
    assert Decimal(str(bal.expected_balance)) == Decimal("2.5")


def test_admin_crypto_custody_includes_actual_expected_mismatch(client: TestClient):
    """GET /api/admin/exchange/crypto-custody returns actual_balance, expected_balance, mismatch when DB has accounts."""
    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    data = res.json()
    accounts = data["accounts"]
    assert len(accounts) >= 2
    for a in accounts:
        assert "actual_balance" in a
        assert "expected_balance" in a
        assert "mismatch" in a
        assert "asset" in a
        assert "account_type" in a
        assert "label" in a


def test_admin_crypto_custody_detail_by_id(client: TestClient):
    """GET /api/admin/exchange/crypto-custody/{id} returns detail for UUID."""
    boot = client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    assert boot.status_code == 200
    first_id = boot.json()["created"][0]["id"]
    res = client.get(f"/api/admin/exchange/crypto-custody/{first_id}", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == first_id
    assert "actual_balance" in data
    assert "expected_balance" in data
    assert "mismatch" in data


def test_set_actual_balance_endpoint(client: TestClient):
    """POST /api/admin/exchange/crypto-custody/{id}/set-actual-balance seeds actual_balance."""
    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    settlement_btc = next(
        a for a in list_res.json()["accounts"]
        if a["asset"] == "BTC" and a["account_type"] == ACCOUNT_TYPE_SETTLEMENT_WALLET
    )
    res = client.post(
        f"/api/admin/exchange/crypto-custody/{settlement_btc['id']}/set-actual-balance",
        json={"actual_balance": "10.5"},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    assert res.json()["actual_balance"] == "10.5"
    detail = client.get(f"/api/admin/exchange/crypto-custody/{settlement_btc['id']}", headers=ADMIN_HEADERS)
    assert float(detail.json()["actual_balance"]) == 10.5


def test_settlement_uses_persisted_balance(client: TestClient, db):
    """run_settlement uses crypto_custody_balances when present (actual_balance for settlement wallet)."""
    from services.exchange.repository import CryptoSettlementDeltaRepository
    from services.exchange.service import ExchangeService
    from services.portfolio_engine.hardening.security.context import ActorContext

    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    settlement_btc = next(
        a for a in list_res.json()["accounts"]
        if a["asset"] == "BTC" and a["account_type"] == ACCOUNT_TYPE_SETTLEMENT_WALLET
    )
    client.post(
        f"/api/admin/exchange/crypto-custody/{settlement_btc['id']}/set-actual-balance",
        json={"actual_balance": "100"},
        headers=ADMIN_HEADERS,
    )
    clear_settlement_wallet_balances()
    delta_repo = CryptoSettlementDeltaRepository()
    delta = delta_repo.get_or_create(db, "BTC", date.today())
    delta_repo.increment(db, delta, Decimal("0.01"))
    db.flush()
    svc = ExchangeService()
    result = svc.run_settlement(db, ActorContext(actor_type="admin", actor_id="test"))
    assert result["settled_count"] >= 1 or (result["blocked_count"] == 0 and result["settled_count"] == 0)
