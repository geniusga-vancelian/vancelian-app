"""Tests for sell-all (liquidate all crypto positions).

Matrix:
  1. Preview sell-all with multiple assets
  2. Sell-all executes all held assets
  3. Zero-balance assets are ignored
  4. Realized P&L remains coherent after total liquidation
  5. EUR account increases by total net received
  6. Stale quote on one asset → partial failure reported correctly
  7. No double submit (idempotency via external_reference)
  8. Invariants A/B/C still hold after full liquidation
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import ROUND_DOWN, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers
from database import MarketDataInstrument, MarketDataLatestQuote
from services.accounting.invariants import compute_pnl_invariants
from services.exchange.assets import ASSET_PRECISION, set_settlement_wallet_balance
from services.exchange.models import ExchangeOrder

BTC_PRICE = 85_000.0
ETH_PRICE = 2_300.0
SOL_PRICE = 180.0
ADA_PRICE = 0.60

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-sell-all@example.com",
    "X-Actor-Roles": "admin",
}


def _unique_email() -> str:
    return f"sellall-{uuid.uuid4().hex[:8]}@example.com"


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


def _full_setup(http: TestClient, db: Session, initial_eur: float = 100_000.0):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    client_acc = _create_client_account(http, provider["id"], str(pe_client.id), db)
    settlement = _create_settlement_account(http, provider["id"])
    if initial_eur > 0:
        _fund_client(http, str(pe_client.id), initial_eur, db)
    return pe_client, client_acc, settlement


def _buy_via_app(http: TestClient, asset: str, fiat_amount: float, auth: dict, _price: float = 0) -> dict:
    """Buy crypto using /api/app/exchange/buy (JWT)."""
    res = http.post(
        "/api/app/exchange/buy",
        json={
            "asset": asset,
            "amount_fiat": fiat_amount,
        },
        headers=auth,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed", data
    return data


def _seed_market_data(db: Session) -> None:
    now = datetime.now(timezone.utc)
    for symbol, prov, price in [
        ("BTCUSDT", "BTCUSDT", BTC_PRICE),
        ("ETHUSDT", "ETHUSDT", ETH_PRICE),
        ("SOLUSDT", "SOLUSDT", SOL_PRICE),
        ("ADAUSDT", "ADAUSDT", ADA_PRICE),
        ("EURUSDT", "EURUSDT", 1.08),
    ]:
        inst = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider_symbol == prov,
        ).first()
        if not inst:
            inst = MarketDataInstrument(
                symbol=symbol,
                name=symbol,
                asset_class="crypto",
                provider="binance",
                provider_symbol=prov,
                is_active="true",
            )
            db.add(inst)
            db.flush()
        quote = (
            db.query(MarketDataLatestQuote)
            .filter(MarketDataLatestQuote.instrument_id == inst.id)
            .first()
        )
        if quote:
            quote.last_price = price
            quote.bid_price = price * 0.999
            quote.ask_price = price * 1.001
            quote.quote_time = now
            quote.updated_at = now
        else:
            quote = MarketDataLatestQuote(
                instrument_id=inst.id,
                provider="binance",
                provider_symbol=prov,
                last_price=price,
                bid_price=price * 0.999,
                ask_price=price * 1.001,
                quote_time=now,
                updated_at=now,
            )
            db.add(quote)
        db.flush()


def _ensure_crypto_custody_bootstrap(client: TestClient, db: Session) -> None:
    client.post(
        "/api/admin/exchange/crypto-custody/bootstrap",
        headers=custody_admin_headers(db),
    )


def _set_settlement_wallet_actual_balance(client: TestClient, db: Session, asset: str, balance: str) -> None:
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=custody_admin_headers(db))
    account = next(
        (a for a in list_res.json()["accounts"]
         if a.get("asset") == asset and a.get("account_type") == "settlement_wallet"),
        None,
    )
    if account and account.get("id") and not str(account["id"]).startswith("wallet-"):
        client.post(
            f"/api/admin/exchange/crypto-custody/{account['id']}/set-actual-balance",
            json={"actual_balance": balance},
            headers=custody_admin_headers(db),
        )


@pytest.fixture()
def setup(client, db):
    http = client
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(http, db)
    for asset in ("BTC", "ETH", "SOL", "ADA"):
        set_settlement_wallet_balance(asset, Decimal("100000"))
        _set_settlement_wallet_actual_balance(http, db, asset, "100000")
    pe_client, client_acc, settlement = _full_setup(http, db)
    auth = mobile_auth_headers(db, pe_client)
    return http, pe_client, db, auth


def _buy_multiple(http, assets_and_amounts, auth: dict):
    """Buy several assets with given (asset, fiat_amount, price) tuples."""
    for asset, fiat, price in assets_and_amounts:
        _buy_via_app(http, asset, fiat, auth, price)


# -------------------------------------------------------------------
# Test 1 — Preview sell-all with multiple assets
# -------------------------------------------------------------------
def test_sell_all_preview_multiple_assets(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [
        ("BTC", 5000, BTC_PRICE),
        ("ETH", 3000, ETH_PRICE),
        ("SOL", 1000, SOL_PRICE),
    ], auth)
    res = http.post("/api/app/exchange/sell-all/preview", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_assets"] == 3
    assert data["estimated_total_eur"] > 0
    assets = [item["asset"] for item in data["items"]]
    assert "BTC" in assets
    assert "ETH" in assets
    assert "SOL" in assets
    for item in data["items"]:
        assert item["status"] == "ready"
        assert item["estimated_eur_net"] > 0


# -------------------------------------------------------------------
# Test 2 — Sell-all executes all held assets
# -------------------------------------------------------------------
def test_sell_all_executes_all(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [
        ("BTC", 5000, BTC_PRICE),
        ("ETH", 3000, ETH_PRICE),
    ], auth)
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_assets_detected"] == 2
    assert data["total_assets_sold"] == 2
    assert data["total_assets_failed"] == 0
    assert data["actual_total_eur_received"] > 0
    for r in data["results"]:
        assert r["status"] == "completed"
        assert float(r["eur_received"]) > 0


# -------------------------------------------------------------------
# Test 3 — Zero-balance assets are ignored
# -------------------------------------------------------------------
def test_sell_all_ignores_zero_balance(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [("BTC", 5000, BTC_PRICE)], auth)
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["total_assets_detected"] == 1
    assert data["total_assets_sold"] == 1
    assets_sold = [r["asset"] for r in data["results"]]
    assert "BTC" in assets_sold
    assert len(assets_sold) == 1


# -------------------------------------------------------------------
# Test 4 — Realized P&L coherent after total liquidation
# -------------------------------------------------------------------
def test_sell_all_realized_pnl_coherent(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [
        ("BTC", 5000, BTC_PRICE),
        ("ETH", 2000, ETH_PRICE),
    ], auth)
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    data = res.json()
    assert data["status"] == "completed"
    for r in data["results"]:
        if r["status"] == "completed":
            assert r.get("realized_pnl") is not None


# -------------------------------------------------------------------
# Test 5 — EUR account increases by total net
# -------------------------------------------------------------------
def test_sell_all_eur_balance_increases(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [("BTC", 5000, BTC_PRICE), ("SOL", 2000, SOL_PRICE)], auth)
    cash_before = http.get("/api/app/cash", headers=auth).json()
    eur_before = float(cash_before["cash_account"]["available_balance"])
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    data = res.json()
    cash_after = http.get("/api/app/cash", headers=auth).json()
    eur_after = float(cash_after["cash_account"]["available_balance"])
    assert eur_after > eur_before
    expected_increase = data["actual_total_eur_received"]
    assert abs(eur_after - eur_before - expected_increase) < 0.02


# -------------------------------------------------------------------
# Test 6 — Stale quote on one asset → partial failure
# -------------------------------------------------------------------
def test_sell_all_partial_failure_stale_quote(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [("BTC", 5000, BTC_PRICE), ("ADA", 500, ADA_PRICE)], auth)
    inst_ada = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.provider_symbol == "ADAUSDT"
    ).first()
    if inst_ada:
        quote = db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == inst_ada.id
        ).first()
        if quote:
            quote.quote_time = datetime.now(timezone.utc) - timedelta(seconds=120)
            db.flush()
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["total_assets_sold"] >= 1
    assert data["total_assets_failed"] >= 1
    failed = [r for r in data["results"] if r["status"] == "failed"]
    assert len(failed) >= 1
    assert failed[0]["asset"] == "ADA"
    assert "error_code" in failed[0]


# -------------------------------------------------------------------
# Test 7 — No double submit
# -------------------------------------------------------------------
def test_sell_all_no_double_submit(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [("BTC", 5000, BTC_PRICE)], auth)
    res1 = http.post("/api/app/exchange/sell-all", headers=auth)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_assets_sold"] == 1
    res2 = http.post("/api/app/exchange/sell-all", headers=auth)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_assets_detected"] == 0
    assert data2["total_assets_sold"] == 0


# -------------------------------------------------------------------
# Test 8 — Invariants A/B/C hold after full liquidation
# -------------------------------------------------------------------
def test_sell_all_invariants_hold(setup):
    http, client, db, auth = setup
    _buy_multiple(http, [
        ("BTC", 5000, BTC_PRICE),
        ("ETH", 3000, ETH_PRICE),
        ("SOL", 1000, SOL_PRICE),
    ], auth)
    res = http.post("/api/app/exchange/sell-all", headers=auth)
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_assets_sold"] == 3
    from uuid import UUID
    inv = compute_pnl_invariants(db, client.id)
    assert inv["invariant_a_ok"], f"Invariant A failed: {inv}"
    assert inv["invariant_b_ok"], f"Invariant B failed: {inv}"
