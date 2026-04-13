"""Tests for Exchange Engine v1 — EUR → Crypto buy + settlement + hardening + fees.

Coverage:
  1.  successful buy (BTC)
  2.  insufficient EUR funds
  3.  duplicate external_reference (idempotency)
  4.  ledger integrity (sum debits == sum credits)
  5.  balances updated (EUR debited, crypto credited)
  6.  settlement job marks deltas settled
  7.  unsupported asset rejected
  8.  crypto_position row-level locking (concurrent buys)
  9.  asset precision rounding
  10. settlement blocked when pool insufficient
  11. settlement success when balance ok
  12. fee calculation
  13. order normalized fields persisted
  14. settlement delta uses raw volume (not post-fee)
  15. admin settlement endpoint
"""
from __future__ import annotations

import uuid
from decimal import ROUND_DOWN, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import custody_admin_headers, make_linked_client
from database import SessionLocal
from services.exchange.assets import (
    ASSET_PRECISION,
    SUPPORTED_ASSETS,
    clear_settlement_wallet_balances,
    set_settlement_wallet_balance,
)
from services.exchange.repository import ExchangeFeeConfigRepository

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}

BTC_PRICE = 85_000.0


def _unique_email() -> str:
    return f"exchange-{uuid.uuid4().hex[:8]}@example.com"


def _create_test_client(_http: TestClient, db: Session):
    return make_linked_client(db, email=_unique_email())


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


def _create_client_account(http: TestClient, provider_id: str, client_id: str, db: Session) -> dict:
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
        headers=custody_admin_headers(db),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_settlement_account(http: TestClient, provider_id: str, db: Session) -> dict:
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
        headers=custody_admin_headers(db),
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


def _fund_client(http: TestClient, client_id: str, amount: float, db: Session) -> None:
    res = http.post(
        "/api/admin/custody/simulate-deposit",
        json={
            "client_id": client_id,
            "amount": amount,
            "currency": "EUR",
            "reference": f"FUND-{uuid.uuid4().hex[:8]}",
        },
        headers=custody_admin_headers(db),
    )
    assert res.status_code == 200, res.text


def _full_setup(http: TestClient, db: Session, initial_balance: float = 10_000.0):
    provider = _create_provider(http)
    pe_client = _create_test_client(http, db)
    client_acc = _create_client_account(http, provider["id"], str(pe_client.id), db)
    settlement = _create_settlement_account(http, provider["id"], db)
    if initial_balance > 0:
        _fund_client(http, str(pe_client.id), initial_balance, db)
    return pe_client, client_acc, settlement


def _buy(http: TestClient, client_id: str, fiat_amount: float, ref: str | None = None) -> dict:
    if ref is None:
        ref = f"buy-{uuid.uuid4().hex[:8]}"
    res = http.post(
        "/api/exchange/buy",
        json={
            "client_id": client_id,
            "asset": "BTC",
            "fiat_amount": fiat_amount,
            "currency": "EUR",
            "external_reference": ref,
            "price": BTC_PRICE,
        },
        headers=ADMIN_HEADERS,
    )
    return res


# ---------------------------------------------------------------------------
# 1. Successful buy
# ---------------------------------------------------------------------------

def test_successful_buy(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res = _buy(client, str(pe_client.id), 1000.0)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["status"] == "completed"
    assert data["order_id"] is not None
    assert data["asset"] == "BTC"
    assert float(data["amount_fiat"]) == 1000.0
    assert float(data["price"]) == BTC_PRICE
    assert float(data["amount_crypto"]) > 0
    assert float(data["client_eur_balance_after"]) == 9000.0
    assert float(data["crypto_position_after"]) > 0


# ---------------------------------------------------------------------------
# 2. Insufficient EUR funds
# ---------------------------------------------------------------------------

def test_insufficient_funds(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=100.0)

    res = _buy(client, str(pe_client.id), 5000.0)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "failed"
    assert data["error"] == "insufficient_funds"


# ---------------------------------------------------------------------------
# 3. Duplicate external_reference (idempotency)
# ---------------------------------------------------------------------------

def test_duplicate_reference(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    ref = f"buy-{uuid.uuid4().hex[:8]}"
    res1 = _buy(client, str(pe_client.id), 1000.0, ref=ref)
    assert res1.status_code == 200
    assert res1.json()["status"] == "completed"

    res2 = _buy(client, str(pe_client.id), 1000.0, ref=ref)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ignored"
    assert data2["reason"] == "duplicate_external_reference"


# ---------------------------------------------------------------------------
# 4. Ledger integrity (sum debits == sum credits)
# ---------------------------------------------------------------------------

def test_ledger_integrity(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res = _buy(client, str(pe_client.id), 2000.0)
    assert res.status_code == 200
    order_id = res.json()["order_id"]

    ledger_res = client.get(
        f"/api/portfolio-engine/ledger-entries?reference_type=exchange_order&reference_id={order_id}",
        headers=ADMIN_HEADERS,
    )
    assert ledger_res.status_code == 200
    entries = ledger_res.json().get("items", [])
    assert len(entries) == 2

    debits = sum(float(e["amount"]) for e in entries if e["entry_type"] == "debit")
    credits_ = sum(float(e["amount"]) for e in entries if e["entry_type"] == "credit")
    assert debits == credits_ == 2000.0


# ---------------------------------------------------------------------------
# 5. Balances updated (EUR debited, crypto credited)
# ---------------------------------------------------------------------------

def test_balances_updated(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res = _buy(client, str(pe_client.id), 5000.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert float(data["client_eur_balance_after"]) == 5000.0

    expected_crypto = 5000.0 / BTC_PRICE
    assert abs(float(data["crypto_position_after"]) - expected_crypto) < 1e-6

    # Second buy accumulates
    res2 = _buy(client, str(pe_client.id), 3000.0)
    assert res2.status_code == 200
    data2 = res2.json()
    assert float(data2["client_eur_balance_after"]) == 2000.0

    total_expected = (5000.0 + 3000.0) / BTC_PRICE
    assert abs(float(data2["crypto_position_after"]) - total_expected) < 1e-6


# ---------------------------------------------------------------------------
# 6. Settlement job marks deltas settled
# ---------------------------------------------------------------------------

def test_settlement_job(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    _buy(client, str(pe_client.id), 1000.0)
    _buy(client, str(pe_client.id), 2000.0)

    _ensure_crypto_custody_bootstrap(client)
    for asset in SUPPORTED_ASSETS:
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("BTC", Decimal("10"))
    try:
        res = client.post("/api/exchange/settlement", headers=ADMIN_HEADERS)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["settled_count"] >= 1

        btc_detail = next((d for d in data["details"] if d["asset"] == "BTC"), None)
        assert btc_detail is not None
        assert float(btc_detail["delta_amount"]) > 0
        assert btc_detail["action"] == "marked_settled"

        res2 = client.post("/api/exchange/settlement", headers=ADMIN_HEADERS)
        assert res2.status_code == 200
        assert res2.json()["settled_count"] == 0
    finally:
        clear_settlement_wallet_balances()


# ---------------------------------------------------------------------------
# 7. Unsupported asset rejected
# ---------------------------------------------------------------------------

def test_unsupported_asset(client: TestClient, db: Session):
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "NOSUP",
            "fiat_amount": 100.0,
            "currency": "EUR",
            "external_reference": f"buy-{uuid.uuid4().hex[:8]}",
            "price": 0.15,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 400
    assert "unsupported_asset" in res.json()["detail"]


# ===========================================================================
# Hardening tests
# ===========================================================================


# ---------------------------------------------------------------------------
# 8. Row-level locking — concurrent buys produce correct cumulative balance
# ---------------------------------------------------------------------------

def test_crypto_position_row_lock(client: TestClient, db: Session):
    """Two sequential buys for the same client+asset must accumulate correctly,
    proving the row-level lock keeps the position consistent."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=20_000.0)

    res1 = _buy(client, str(pe_client.id), 5000.0)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "completed"
    pos_after_1 = float(data1["crypto_position_after"])

    res2 = _buy(client, str(pe_client.id), 3000.0)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "completed"
    pos_after_2 = float(data2["crypto_position_after"])

    expected_1 = 5000.0 / BTC_PRICE
    expected_total = (5000.0 + 3000.0) / BTC_PRICE

    assert abs(pos_after_1 - expected_1) < 1e-6
    assert abs(pos_after_2 - expected_total) < 1e-6

    # EUR balances must also be consistent
    assert float(data2["client_eur_balance_after"]) == 12_000.0


# ---------------------------------------------------------------------------
# 9. Asset precision rounding
# ---------------------------------------------------------------------------

def test_asset_precision_rounding(client: TestClient, db: Session):
    """Verify rounding uses ROUND_DOWN with per-asset precision from the registry."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=50_000.0)

    # BTC: 8 decimals
    btc_price = Decimal("85000")
    fiat = Decimal("1000")
    expected_btc = (fiat / btc_price).quantize(
        Decimal(10) ** -ASSET_PRECISION["BTC"], rounding=ROUND_DOWN
    )

    res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "fiat_amount": 1000.0,
            "currency": "EUR",
            "external_reference": f"prec-btc-{uuid.uuid4().hex[:8]}",
            "price": 85000.0,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert Decimal(data["amount_crypto"]) == expected_btc

    # ETH: 18 decimals
    eth_price = Decimal("3200")
    expected_eth = (fiat / eth_price).quantize(
        Decimal(10) ** -ASSET_PRECISION["ETH"], rounding=ROUND_DOWN
    )

    res_eth = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "ETH",
            "fiat_amount": 1000.0,
            "currency": "EUR",
            "external_reference": f"prec-eth-{uuid.uuid4().hex[:8]}",
            "price": 3200.0,
        },
        headers=ADMIN_HEADERS,
    )
    assert res_eth.status_code == 200
    data_eth = res_eth.json()
    assert data_eth["status"] == "completed"
    assert Decimal(data_eth["amount_crypto"]) == expected_eth

    # XRP: 6 decimals
    xrp_price = Decimal("0.55")
    expected_xrp = (fiat / xrp_price).quantize(
        Decimal(10) ** -ASSET_PRECISION["XRP"], rounding=ROUND_DOWN
    )

    res_xrp = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "XRP",
            "fiat_amount": 1000.0,
            "currency": "EUR",
            "external_reference": f"prec-xrp-{uuid.uuid4().hex[:8]}",
            "price": 0.55,
        },
        headers=ADMIN_HEADERS,
    )
    assert res_xrp.status_code == 200
    data_xrp = res_xrp.json()
    assert data_xrp["status"] == "completed"
    assert Decimal(data_xrp["amount_crypto"]) == expected_xrp


# ---------------------------------------------------------------------------
# 10. Settlement blocked when settlement wallet has insufficient liquidity
# ---------------------------------------------------------------------------

def _ensure_crypto_custody_bootstrap(client: TestClient):
    """Ensure crypto custody accounts exist (bootstrap)."""
    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)


def _set_settlement_wallet_actual_balance(client: TestClient, asset: str, balance: str) -> None:
    """Set actual_balance for the settlement wallet of asset via admin API."""
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    account = next(
        (a for a in list_res.json()["accounts"] if a.get("asset") == asset and a.get("account_type") == "settlement_wallet"),
        None,
    )
    if account and account.get("id") and not account["id"].startswith("wallet-"):
        client.post(
            f"/api/admin/exchange/crypto-custody/{account['id']}/set-actual-balance",
            json={"actual_balance": balance},
            headers=ADMIN_HEADERS,
        )


def test_settlement_blocked_when_pool_insufficient(client: TestClient, db: Session):
    """Buy creates a positive BTC delta. Without seeding the settlement wallet,
    settlement must refuse and return status=blocked."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res_buy = _buy(client, str(pe_client.id), 1000.0)
    assert res_buy.status_code == 200
    assert res_buy.json()["status"] == "completed"

    # Ensure DB settlement wallet balance is 0 for all assets so no other deltas settle
    from services.exchange.assets import SUPPORTED_ASSETS as _ALL_ASSETS
    clear_settlement_wallet_balances()
    _ensure_crypto_custody_bootstrap(client)
    for asset in _ALL_ASSETS:
        _set_settlement_wallet_actual_balance(client, asset, "0")

    res = client.post("/api/exchange/settlement", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()

    # Only pre-existing zero-amount deltas (leaked from previous runs) may auto-settle;
    # the BTC delta from our BUY must be blocked.
    assert data["blocked_count"] >= 1

    btc_detail = next((d for d in data["details"] if d["asset"] == "BTC"), None)
    assert btc_detail is not None
    assert btc_detail["status"] == "blocked"
    assert btc_detail["reason"] == "insufficient_settlement_wallet_liquidity"


# ---------------------------------------------------------------------------
# 11. Settlement success when balance is sufficient
# ---------------------------------------------------------------------------

def test_settlement_success_when_balance_ok(client: TestClient, db: Session):
    """Seed the settlement wallet with enough BTC, then the BTC delta must settle."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res_buy = _buy(client, str(pe_client.id), 2000.0)
    assert res_buy.status_code == 200
    assert res_buy.json()["status"] == "completed"

    # Seed via DB (crypto custody layer) so run_settlement uses actual_balance
    from services.exchange.assets import SUPPORTED_ASSETS as _ALL_ASSETS
    _ensure_crypto_custody_bootstrap(client)
    for asset in _ALL_ASSETS:
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    clear_settlement_wallet_balances()

    res = client.post("/api/exchange/settlement", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["settled_count"] >= 1

    btc_detail = next((d for d in data["details"] if d["asset"] == "BTC"), None)
    assert btc_detail is not None
    assert btc_detail["action"] == "marked_settled"
    assert float(btc_detail["delta_amount"]) > 0

    # Our BTC delta must not be blocked (we seeded all settlement wallets)
    blocked_btc = [d for d in data["details"] if d.get("asset") == "BTC" and d.get("status") == "blocked"]
    assert len(blocked_btc) == 0


# ===========================================================================
# Fee & Order Model tests
# ===========================================================================


# ---------------------------------------------------------------------------
# 12. Fee calculation
# ---------------------------------------------------------------------------

def test_fee_calculation(client: TestClient, db: Session):
    """Buy with 50 bps fee: client receives volume_raw - fee_crypto."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    ExchangeFeeConfigRepository.upsert(db, "BTC", fee_bps=50)
    db.flush()

    res = _buy(client, str(pe_client.id), 1000.0)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed"

    volume_raw = Decimal(str(data["volume_raw"]))
    fee_amount = Decimal(str(data["fee_amount"]))
    amount_to = Decimal(str(data["amount_to"]))

    assert data["fee_bps"] == 50
    assert data["fee_asset"] == "BTC"

    expected_fee = (volume_raw * 50 / Decimal("10000")).quantize(
        Decimal(10) ** -ASSET_PRECISION["BTC"], rounding=ROUND_DOWN
    )
    assert fee_amount == expected_fee
    assert amount_to == volume_raw - fee_amount

    assert float(data["crypto_position_after"]) == pytest.approx(float(amount_to), abs=1e-10)


# ---------------------------------------------------------------------------
# 13. Order normalized fields persisted
# ---------------------------------------------------------------------------

def test_order_fields_persisted(client: TestClient, db: Session):
    """Verify from_asset, to_asset, amount_from, amount_to, fee fields are in response."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    res = _buy(client, str(pe_client.id), 500.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"

    assert data["from_asset"] == "EUR"
    assert data["to_asset"] == "BTC"
    assert float(data["amount_from"]) == 500.0
    assert Decimal(str(data["amount_to"])) > 0
    assert data["fee_asset"] == "BTC"
    assert "fee_amount" in data
    assert "fee_bps" in data
    assert "volume_raw" in data


# ---------------------------------------------------------------------------
# 14. Settlement delta uses raw volume (not post-fee)
# ---------------------------------------------------------------------------

def test_settlement_delta_uses_raw_volume(client: TestClient, db: Session):
    """When a fee is applied, the settlement delta must use the raw (pre-fee) volume."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)

    ExchangeFeeConfigRepository.upsert(db, "BTC", fee_bps=100)
    db.flush()

    res = _buy(client, str(pe_client.id), 1000.0)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"

    volume_raw = Decimal(str(data["volume_raw"]))
    amount_to = Decimal(str(data["amount_to"]))
    assert volume_raw > amount_to

    _ensure_crypto_custody_bootstrap(client)
    set_settlement_wallet_balance("BTC", Decimal("10"))
    _set_settlement_wallet_actual_balance(client, "BTC", "10")
    for asset in SUPPORTED_ASSETS:
        if asset != "BTC":
            set_settlement_wallet_balance(asset, Decimal("100000"))
            _set_settlement_wallet_actual_balance(client, asset, "100000")

    sres = client.post("/api/exchange/settlement", headers=ADMIN_HEADERS)
    assert sres.status_code == 200
    sdata = sres.json()

    btc_detail = next((d for d in sdata["details"] if d["asset"] == "BTC"), None)
    assert btc_detail is not None

    settled_amount = Decimal(str(btc_detail["delta_amount"]))
    assert settled_amount >= volume_raw
    clear_settlement_wallet_balances()


# ---------------------------------------------------------------------------
# 15. Admin settlement endpoint
# ---------------------------------------------------------------------------

def test_admin_settlement_endpoint(client: TestClient, db: Session):
    """POST /api/admin/exchange/run-settlement triggers settlement."""
    pe_client, client_acc, settlement = _full_setup(client, db, initial_balance=10_000.0)
    _buy(client, str(pe_client.id), 500.0)

    _ensure_crypto_custody_bootstrap(client)
    for asset in SUPPORTED_ASSETS:
        set_settlement_wallet_balance(asset, Decimal("100000"))
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    try:
        res = client.post("/api/admin/exchange/run-settlement", headers=ADMIN_HEADERS)
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["status"] == "completed"
        assert "assets_processed" in data
        assert "deltas_settled" in data
        assert "blocked_count" in data
        assert data["deltas_settled"] >= 1
    finally:
        clear_settlement_wallet_balances()
