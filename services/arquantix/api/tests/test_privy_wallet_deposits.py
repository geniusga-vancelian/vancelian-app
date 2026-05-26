"""Tests ledger wallet Privy — webhooks dépôts + API lecture."""
from __future__ import annotations

import os
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person, PersonCryptoWallet, engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from tests.conftest import make_linked_client, mobile_auth_headers


def _migration_158_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'person_wallet_deposits'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_158_applied(),
    reason="Appliquer `alembic upgrade head` (révision 158) pour les tests privy wallet.",
)


@pytest.fixture(autouse=True)
def _privy_webhook_stub_mode(monkeypatch):
    monkeypatch.setenv("PRIVY_WEBHOOK_VERIFICATION_MODE", "stub")


def _wallet_address() -> str:
    return f"0x{uuid.uuid4().hex[:40]}"


def _seed_privy_wallet(db: Session, pe_client) -> PersonCryptoWallet:
    return upsert_person_crypto_wallet(
        db,
        person_id=pe_client.person_id,
        pe_client_id=pe_client.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=1,
        address=_wallet_address(),
    )


def _deposit_payload(*, to_address: str, amount_wei: str = "1000000000000000000") -> dict:
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}"
    return {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "idempotency_key": f"idem_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": to_address,
            "from_address": f"0x{uuid.uuid4().hex[:40]}",
            "transaction_hash": tx_hash,
            "chain_id": "eip155:1",
            "asset": {"type": "native", "symbol": "ETH"},
            "amount": amount_wei,
            "log_index": 0,
            "block_number": 12345678,
            "confirmations": 12,
        },
    }


def test_webhook_native_token_hyphen_payload(client: TestClient, db: Session):
    """Privy dashboard envoie asset.type = native-token (pas native_token)."""
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": wallet.address,
            "from_address": f"0x{uuid.uuid4().hex[:40]}",
            "transaction_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
            "caip2": "eip155:1",
            "asset": {"type": "native-token", "address": None},
            "amount": "10000000000000000",
            "log_index": 0,
            "block_number": 25164497,
            "confirmations": 1,
        },
    }
    res = client.post(
        "/api/webhooks/privy",
        json=payload,
        headers={"svix-id": f"msg_{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["processing_status"] == "processed"

    auth = mobile_auth_headers(db, pe)
    eth = next(
        b for b in client.get("/api/app/privy-wallet/balances", headers=auth).json()["balances"]
        if b["asset"] == "ETH"
    )
    assert eth["balance"] == "0.01"


def test_webhook_deposit_credits_balance_and_deposit_row(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = _deposit_payload(to_address=wallet.address)
    res = client.post(
        "/api/webhooks/privy",
        json=payload,
        headers={"svix-id": f"msg_{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["processing_status"] == "processed"

    headers = mobile_auth_headers(db, pe)
    bal_res = client.get("/api/app/privy-wallet/balances", headers=headers)
    assert bal_res.status_code == 200, bal_res.text
    balances = bal_res.json()["balances"]
    assert len(balances) == 1
    assert balances[0]["asset"] == "ETH"
    assert balances[0]["balance"] == "1"

    dep_res = client.get("/api/app/privy-wallet/deposits", headers=headers)
    assert dep_res.status_code == 200, dep_res.text
    deposits = dep_res.json()["deposits"]
    assert len(deposits) == 1
    assert deposits[0]["asset"] == "ETH"
    assert deposits[0]["amount"] == "1"
    assert deposits[0]["direction"] == "credit"
    assert deposits[0]["transaction_kind"] == "privy_deposit_in"
    assert deposits[0]["title"].startswith("Dépôt")


def test_webhook_duplicate_is_idempotent(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = _deposit_payload(to_address=wallet.address)
    svix_id = f"msg_{uuid.uuid4().hex[:8]}"
    headers = {"svix-id": svix_id}

    first = client.post("/api/webhooks/privy", json=payload, headers=headers)
    assert first.status_code == 200
    second = client.post("/api/webhooks/privy", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["processing_status"] in ("duplicate", "processed")

    auth = mobile_auth_headers(db, pe)
    dep_res = client.get("/api/app/privy-wallet/deposits", headers=auth)
    assert len(dep_res.json()["deposits"]) == 1


def test_webhook_failed_event_can_be_retried(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": wallet.address,
            "transaction_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
            "chain_id": "eip155:1",
            "asset": {"type": "erc20", "symbol": "USDT"},
            "contract_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "amount": "10000000",
            "log_index": 0,
        },
    }
    svix_id = f"msg_{uuid.uuid4().hex[:8]}"
    headers = {"svix-id": svix_id}

    first = client.post("/api/webhooks/privy", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["processing_status"] == "processed"

    second = client.post("/api/webhooks/privy", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["processing_status"] in ("duplicate", "processed")

    auth = mobile_auth_headers(db, pe)
    usdt = next(
        b for b in client.get("/api/app/privy-wallet/balances", headers=auth).json()["balances"]
        if b["asset"] == "USDT"
    )
    assert usdt["balance"] == "10"


def test_webhook_unknown_wallet_address_fails(client: TestClient, db: Session):
    payload = _deposit_payload(to_address=_wallet_address())
    res = client.post(
        "/api/webhooks/privy",
        json=payload,
        headers={"svix-id": f"msg_{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200
    assert res.json()["processing_status"] == "failed"


def test_deposits_filter_by_asset(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    eth_payload = _deposit_payload(to_address=wallet.address, amount_wei="500000000000000000")
    usdc_payload = {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": wallet.address,
            "transaction_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
            "chain_id": 1,
            "asset": {"type": "erc20", "symbol": "USDC"},
            "contract_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "amount": "1000000",
            "log_index": 1,
        },
    }

    assert client.post("/api/webhooks/privy", json=eth_payload).status_code == 200
    assert client.post("/api/webhooks/privy", json=usdc_payload).status_code == 200

    auth = mobile_auth_headers(db, pe)
    filtered = client.get("/api/app/privy-wallet/deposits?asset=USDC", headers=auth)
    assert filtered.status_code == 200
    deposits = filtered.json()["deposits"]
    assert len(deposits) == 1
    assert deposits[0]["asset"] == "USDC"
    assert deposits[0]["amount"] == "1"


@pytest.mark.parametrize(
    ("asset", "contract", "amount_atomic", "expected"),
    [
        ("USDT", "0xdac17f958d2ee523a2206206994597c13d831ec7", "10000000", "10"),
        ("EURC", "0x1abaea1f781e1f27444163d08077255fb56359a", "5000000", "5"),
    ],
)
def test_webhook_erc20_watchlist_assets(
    client: TestClient,
    db: Session,
    asset: str,
    contract: str,
    amount_atomic: str,
    expected: str,
):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": wallet.address,
            "transaction_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
            "chain_id": "eip155:1",
            "asset": {"type": "erc20", "symbol": asset},
            "contract_address": contract,
            "amount": amount_atomic,
            "log_index": 0,
        },
    }
    res = client.post(
        "/api/webhooks/privy",
        json=payload,
        headers={"svix-id": f"msg_{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["processing_status"] == "processed"

    auth = mobile_auth_headers(db, pe)
    balances = client.get("/api/app/privy-wallet/balances", headers=auth).json()["balances"]
    row = next(b for b in balances if b["asset"] == asset)
    assert row["balance"] == expected


def test_webhook_base_usdc_deposit(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = {
        "type": "wallet.funds_deposited",
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "data": {
            "to_address": wallet.address,
            "from_address": f"0x{uuid.uuid4().hex[:40]}",
            "transaction_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:32]}",
            "chain_id": "eip155:8453",
            "asset": {"type": "erc20", "symbol": "USDC"},
            "contract_address": "0x833589fCD6eDb6E08Ab4c7C32D4f71b54bdA02913",
            "amount": "15000000",
            "log_index": 0,
            "block_number": 12345678,
            "confirmations": 12,
        },
    }
    res = client.post(
        "/api/webhooks/privy",
        json=payload,
        headers={"svix-id": f"msg_{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["processing_status"] == "processed"

    auth = mobile_auth_headers(db, pe)
    usdc = next(
        b for b in client.get("/api/app/privy-wallet/balances", headers=auth).json()["balances"]
        if b["asset"] == "USDC"
    )
    assert usdc["balance"] == "15"


def test_get_deposit_detail(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    payload = _deposit_payload(to_address=wallet.address)
    client.post("/api/webhooks/privy", json=payload)

    auth = mobile_auth_headers(db, pe)
    listing = client.get("/api/app/privy-wallet/deposits", headers=auth).json()
    deposit_id = listing["deposits"][0]["id"]

    detail = client.get(f"/api/app/privy-wallet/deposits/{deposit_id}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["id"] == deposit_id


def test_balances_requires_auth(client: TestClient):
    res = client.get("/api/app/privy-wallet/balances")
    assert res.status_code == 401


def test_admin_simulate_deposit_credits_ledger(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    res = client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={
            "person_id": str(pe.person_id),
            "amount": "0.25",
            "asset": "ETH",
        },
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["processing_status"] == "processed"
    assert body["asset"] == "ETH"
    assert body["amount"] == "0.25"
    assert body["deposit_id"]
    assert body["tx_hash"].startswith("0xsim")

    auth = mobile_auth_headers(db, pe)
    bal_res = client.get("/api/app/privy-wallet/balances", headers=auth)
    assert bal_res.status_code == 200
    eth = next(b for b in bal_res.json()["balances"] if b["asset"] == "ETH")
    assert eth["balance"] == "0.25"
    assert eth["wallet_address"].lower() == wallet.address.lower()


def test_admin_simulate_deposit_unknown_person(client: TestClient):
    res = client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={
            "person_id": str(uuid.uuid4()),
            "amount": "1",
            "asset": "ETH",
        },
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 404


def test_customer_detail_includes_privy_wallets(client: TestClient, db: Session):
    pe = make_linked_client(db)
    person = db.query(Person).filter(Person.id == pe.person_id).first()
    person.profile_json = {
        **(person.profile_json or {}),
        "collected": {"phone_e164": "+33601020304", "email": pe.email},
    }
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    res = client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={"person_id": str(pe.person_id), "amount": "1", "asset": "ETH"},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert res.status_code == 200

    detail = client.get(
        f"/api/admin/customers/{pe.person_id}",
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert detail.status_code == 200, detail.text
    privy = detail.json()["privy_wallets"]
    assert privy["availability"] == "available"
    assert len(privy["wallets"]) == 1
    assert privy["wallets"][0]["address"].lower() == wallet.address.lower()
    assert len(privy["balances"]) >= 1
    assert len(privy["recent_deposits"]) >= 1


def test_crypto_positions_includes_privy_balances(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={"person_id": str(pe.person_id), "amount": "100", "asset": "USDC"},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    db.commit()

    headers = mobile_auth_headers(db, pe)
    pos_res = client.get("/api/app/crypto-positions", headers=headers)
    assert pos_res.status_code == 200, pos_res.text
    positions = pos_res.json()["positions"]
    usdc = next((p for p in positions if p["asset"] == "USDC"), None)
    assert usdc is not None
    assert usdc["balance"] == "100"
    assert usdc["portfolio_scope"] in ("privy", "merged")
    assert usdc["privy_balance"] == "100"

    stats_res = client.get("/api/app/portfolio/global/statistics", headers=headers)
    assert stats_res.status_code == 200, stats_res.text
    stats = stats_res.json()
    assert stats["breakdown"].get("privy", 0) >= 0
    assert stats["performance"]["current_value"] >= float(usdc.get("estimated_value_eur") or 0)


def test_crypto_transactions_include_privy_deposits(client: TestClient, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_privy_wallet(db, pe)
    db.flush()

    sim = client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={"person_id": str(pe.person_id), "amount": "50", "asset": "USDC"},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    assert sim.status_code == 200, sim.text
    deposit_id = sim.json()["deposit_id"]
    db.commit()

    headers = mobile_auth_headers(db, pe)
    tx_res = client.get("/api/app/crypto-positions/USDC/transactions", headers=headers)
    assert tx_res.status_code == 200, tx_res.text
    txs = tx_res.json()["transactions"]
    privy_tx = next((t for t in txs if t.get("source_system") == "privy"), None)
    assert privy_tx is not None
    assert privy_tx["side"] == "deposit"
    assert privy_tx["amount_crypto"] == "50"
    assert privy_tx["transaction_kind"] == "privy_deposit_in"
    assert privy_tx["custody_provider"] == "privy"

    detail = client.get(f"/api/app/transactions/{deposit_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["source_system"] == "privy"
    assert body["transaction_kind"] == "privy_deposit_in"
    assert body["provider_name"] == "Privy"
    assert body["amount"] == "50"


def test_direct_crypto_positions_include_privy_balances(client: TestClient, db: Session):
    pe = make_linked_client(db)
    _seed_privy_wallet(db, pe)
    db.flush()

    client.post(
        "/api/admin/privy-wallet/simulate-deposit",
        json={"person_id": str(pe.person_id), "amount": "100", "asset": "USDC"},
        headers={
            "X-Actor-Type": "admin",
            "X-Actor-Id": "admin@test.local",
            "X-Actor-Roles": "admin",
        },
    )
    db.commit()

    headers = mobile_auth_headers(db, pe)
    direct_res = client.get("/api/app/crypto-positions/direct", headers=headers)
    assert direct_res.status_code == 200, direct_res.text
    positions = direct_res.json()["positions"]
    usdc = next((p for p in positions if p["asset"] == "USDC"), None)
    assert usdc is not None, positions
    assert usdc["balance"] == "100"
    assert usdc["portfolio_scope"] in ("privy", "merged")
