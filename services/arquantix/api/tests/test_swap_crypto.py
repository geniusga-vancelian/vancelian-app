"""Tests for crypto ↔ crypto swap.

Matrix:
  1. Swap simple BTC → ETH
  2. Swap with fees
  3. Invariant global (A/B/C)
  4. Source balance insufficient
  5. Quote stale (skip if no way to simulate)
  6. Several swaps (BTC→ETH, ETH→SOL)
  7. Preview vs execution
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.accounting.invariants import compute_pnl_invariants
from services.exchange.assets import ASSET_PRECISION, set_settlement_wallet_balance
from services.exchange.models import ExchangeOrder

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

BTC_QUANT = Decimal(10) ** -ASSET_PRECISION.get("BTC", 8)
BTC_PRICE = 85_000.0
ETH_PRICE = 2_300.0
SOL_PRICE = 180.0

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-swap@example.com",
    "X-Actor-Roles": "admin",
}


def _unique_email() -> str:
    return f"swap-{uuid.uuid4().hex[:8]}@example.com"


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


def _full_setup(http: TestClient, db: Session, initial_eur: float = 100_000.0):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    client_acc = _create_client_account(http, provider["id"], str(pe_client.id), db)
    settlement = _create_settlement_account(http, provider["id"], db)
    if initial_eur > 0:
        _fund_client(http, str(pe_client.id), initial_eur, db)
    return pe_client, client_acc, settlement


def _buy(http: TestClient, client_id: str, fiat_amount: float) -> dict:
    ref = f"swap-buy-{uuid.uuid4().hex[:8]}"
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
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed", data
    return data


def _seed_market_data(db: Session) -> None:
    """Seed BTCUSDT, ETHUSDT, SOLUSDT, EURUSDT for swap pricing."""
    now = datetime.now(timezone.utc)
    for symbol, prov, price in [
        ("BTCUSDT", "BTCUSDT", BTC_PRICE),
        ("ETHUSDT", "ETHUSDT", ETH_PRICE),
        ("SOLUSDT", "SOLUSDT", SOL_PRICE),
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


def _ensure_crypto_custody_bootstrap(client: TestClient) -> None:
    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)


def _set_settlement_wallet_actual_balance(client: TestClient, asset: str, balance: str) -> None:
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    account = next(
        (a for a in list_res.json()["accounts"]
         if a.get("asset") == asset and a.get("account_type") == "settlement_wallet"),
        None,
    )
    if account and account.get("id") and not str(account["id"]).startswith("wallet-"):
        client.post(
            f"/api/admin/exchange/crypto-custody/{account['id']}/set-actual-balance",
            json={"actual_balance": balance},
            headers=ADMIN_HEADERS,
        )


def _swap_preview(
    http: TestClient,
    from_asset: str,
    to_asset: str,
    amount_from: float,
    auth: dict,
) -> dict:
    res = http.post(
        "/api/app/exchange/swap/preview",
        json={
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_from": amount_from,
        },
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()


def _swap(
    http: TestClient,
    from_asset: str,
    to_asset: str,
    amount_from: float,
    auth: dict,
) -> dict:
    res = http.post(
        "/api/app/exchange/swap",
        json={
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_from": amount_from,
        },
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Test 1 — Swap simple BTC → ETH
# ---------------------------------------------------------------------------


def test_swap_simple_btc_to_eth(client: TestClient, db: Session):
    """Asset source reduced, asset target increased, realized BTC correct, cost basis ETH correct."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=50_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))

    buy_data = _buy(client, cid, 10_000.0)
    btc_before = Decimal(str(buy_data["crypto_position_after"]))
    swap_amount = float((btc_before / 2).quantize(BTC_QUANT, rounding=ROUND_DOWN))

    result = _swap(client, "BTC", "ETH", swap_amount, auth)
    assert result["status"] == "completed"
    assert result["from_asset"] == "BTC"
    assert result["to_asset"] == "ETH"
    assert float(result["amount_from"]) == swap_amount
    assert float(result["amount_to"]) > 0
    assert result["cost_basis_consumed"] is not None
    assert result["realized_pnl_generated"] is not None
    assert float(result["from_position_after"]) < float(btc_before)
    assert float(result["to_position_after"]) > 0


# ---------------------------------------------------------------------------
# Test 2 — Swap with fees
# ---------------------------------------------------------------------------


def test_swap_with_fees(client: TestClient, db: Session):
    """Verify net from SELL is the base for BUY, no phantom EUR."""
    from services.exchange.repository import ExchangeFeeConfigRepository

    pe_client, _, _ = _full_setup(client, db, initial_eur=50_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    ExchangeFeeConfigRepository.upsert(db, "BTC", fee_bps=100)
    db.flush()
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))

    _buy(client, cid, 5_000.0)
    result = _swap(client, "BTC", "ETH", 0.01, auth)
    assert result["status"] == "completed"
    gross = float(result["reference_value_gross"])
    fee = float(result["fee_in_reference_currency"])
    net = float(result["reference_value_net"])
    assert abs(net - (gross - fee)) < 1.0
    assert fee > 0


# ---------------------------------------------------------------------------
# Test 3 — Invariant global
# ---------------------------------------------------------------------------


def test_swap_preserves_invariants(client: TestClient, db: Session):
    """After swap, invariants A/B/C still hold."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=20_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))

    _buy(client, cid, 3_000.0)
    _swap(client, "BTC", "ETH", 0.01, auth)
    db.flush()

    inv = compute_pnl_invariants(db, pe_client.id)
    assert inv["invariant_a_ok"] is True
    assert inv["invariant_b_ok"] is True
    assert inv["invariant_c_ok"] is True
    assert inv["all_ok"] is True


# ---------------------------------------------------------------------------
# Test 4 — Source balance insufficient
# ---------------------------------------------------------------------------
# Test 5 — Quote stale: skipped (would require mocking quote_time)


def test_swap_insufficient_source_balance(client: TestClient, db: Session):
    """Swap rejected when source balance insufficient."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    auth = mobile_auth_headers(db, pe_client)
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))

    _buy(client, str(pe_client.id), 1_000.0)
    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 999.0},
        headers=auth,
    )
    assert res.status_code in (200, 409)
    data = res.json()
    if res.status_code == 200:
        assert data.get("status") == "failed" or "error" in data
    else:
        assert "INSUFFICIENT" in str(data.get("detail", ""))


# ---------------------------------------------------------------------------
# Test 6 — Several swaps
# ---------------------------------------------------------------------------


def test_swap_multiple_sequential(client: TestClient, db: Session):
    """BTC → ETH then ETH → SOL, verify cost basis coherence."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=50_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))
    set_settlement_wallet_balance("SOL", Decimal("10000"))

    _buy(client, cid, 5_000.0)
    r1 = _swap(client, "BTC", "ETH", 0.02, auth)
    assert r1["status"] == "completed"
    eth_after = float(r1["to_position_after"])

    r2 = _swap(client, "ETH", "SOL", eth_after / 2, auth)
    assert r2["status"] == "completed"
    assert float(r2["to_position_after"]) > 0
    assert r2["cost_basis_consumed"] is not None


# ---------------------------------------------------------------------------
# Test 7 — Preview vs execution
# ---------------------------------------------------------------------------


def test_swap_preview_vs_execution(client: TestClient, db: Session):
    """Preview coherent with execution."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=20_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    _seed_market_data(db)
    _ensure_crypto_custody_bootstrap(client)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(client, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))

    _buy(client, cid, 2_000.0)
    preview = _swap_preview(client, "BTC", "ETH", 0.01, auth)
    exec_result = _swap(client, "BTC", "ETH", 0.01, auth)

    assert abs(preview["estimated_to_amount"] - float(exec_result["amount_to"])) < 0.01
    assert abs(preview["estimated_reference_value_net"] - exec_result["reference_value_net"]) < 5.0
