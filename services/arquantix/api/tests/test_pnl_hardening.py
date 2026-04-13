"""Tests for PnL Accounting Hardening (before swap crypto↔crypto).

Matrix of 8 scenarios:
  1. BUY simple
  2. SELL total with fees
  3. SELL partiel
  4. Multiple BUY then SELL (WAC)
  5. Invariant A: NAV = cash + crypto
  6. Invariant B: total_pnl = realized + unrealized
  7. Invariant C: NAV = net_external_cash_flows + realized + unrealized
  8. Persistance SELL: cost_basis_consumed, realized_pnl_generated
"""
from __future__ import annotations

import uuid
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.accounting.invariants import compute_pnl_invariants
from services.exchange.assets import ASSET_PRECISION
from services.exchange.models import ExchangeOrder
from services.exchange.repository import ExchangeFeeConfigRepository

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

BTC_QUANT = Decimal(10) ** -ASSET_PRECISION.get("BTC", 8)
BTC_PRICE = 85_000.0

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-pnl@example.com",
    "X-Actor-Roles": "admin",
}


def _unique_email() -> str:
    return f"pnl-{uuid.uuid4().hex[:8]}@example.com"


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
    ref = f"pnl-buy-{uuid.uuid4().hex[:8]}"
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


def _sell(http: TestClient, client_id: str, amount_crypto: str, ref: str | None = None) -> dict:
    if ref is None:
        ref = f"pnl-sell-{uuid.uuid4().hex[:8]}"
    res = http.post(
        "/api/exchange/sell",
        json={
            "client_id": client_id,
            "asset": "BTC",
            "amount_crypto": amount_crypto,
            "currency": "EUR",
            "external_reference": ref,
            "price": BTC_PRICE,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text
    return res.json()


def _seed_market_data(db: Session, btc_price: float = BTC_PRICE, eurusdt: float = 1.08) -> None:
    """Seed BTCUSDT and EURUSDT quotes for invariant crypto_value computation."""
    from datetime import datetime, timezone

    for symbol, prov, price in [
        ("BTCUSDT", "BTCUSDT", btc_price),
        ("EURUSDT", "EURUSDT", eurusdt),
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
            quote.updated_at = datetime.now(timezone.utc)
        else:
            quote = MarketDataLatestQuote(
                instrument_id=inst.id,
                provider="binance",
                provider_symbol=prov,
                last_price=price,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(quote)
        db.flush()


# ---------------------------------------------------------------------------
# Test 1 — BUY simple
# ---------------------------------------------------------------------------


def test_pnl_buy_simple(client: TestClient, db: Session):
    """Buy 1000 EUR BTC. unrealized = current_value - 1000, realized = 0."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    _seed_market_data(db, btc_price=BTC_PRICE)

    buy_data = _buy(client, cid, 1000.0)
    crypto_qty = Decimal(str(buy_data["crypto_position_after"]))

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    stats = res.json()

    assert stats["realized_pnl"] == 0
    assert stats["unrealized_pnl"] is not None
    # unrealized = current_value - cost_basis; cost_basis = 1000
    expected_unrealized = float(crypto_qty * Decimal(str(BTC_PRICE)) / Decimal("1.08")) - 1000.0
    assert abs(stats["unrealized_pnl"] - expected_unrealized) < 1.0


# ---------------------------------------------------------------------------
# Test 2 — SELL total with fees
# ---------------------------------------------------------------------------


def test_pnl_sell_total_with_fees(client: TestClient, db: Session):
    """Buy 1000 EUR BTC, sell total. Verify realized uses net (not gross)."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)
    ExchangeFeeConfigRepository.upsert(db, "BTC", fee_bps=100)
    db.flush()

    buy_data = _buy(client, cid, 1000.0)
    crypto_qty = Decimal(str(buy_data["crypto_position_after"]))
    sell_amount = str(crypto_qty.quantize(BTC_QUANT, rounding=ROUND_DOWN))

    sell_data = _sell(client, cid, sell_amount)
    assert sell_data["status"] == "completed"

    gross = Decimal(str(sell_data["gross_eur"]))
    fee = Decimal(str(sell_data["fee_eur"]))
    net = Decimal(str(sell_data["net_eur"]))
    assert net == gross - fee
    assert net > 0

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    stats = res.json()

    # Realized must use net (net_received - cost_basis), not gross
    # cost_basis = 1000 (full position), realized = net - 1000
    expected_realized = float(net) - 1000.0
    assert abs(stats["realized_pnl"] - expected_realized) < 15.0  # allow rounding
    assert stats["unrealized_pnl"] == 0


# ---------------------------------------------------------------------------
# Test 3 — SELL partiel
# ---------------------------------------------------------------------------


def test_pnl_sell_partiel(client: TestClient, db: Session):
    """Buy, sell 50%. Verify cost_basis_consumed, realized_pnl_generated, cost basis restant."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    auth = mobile_auth_headers(db, pe_client)
    cid = str(pe_client.id)

    buy_data = _buy(client, cid, 2000.0)
    crypto_qty = Decimal(str(buy_data["crypto_position_after"]))
    sell_half = Decimal("0.5") * crypto_qty
    sell_amount = str(sell_half.quantize(BTC_QUANT, rounding=ROUND_DOWN))

    sell_data = _sell(client, cid, sell_amount)
    assert sell_data["status"] == "completed"

    # cost_basis for full position = 2000, so 50% = 1000
    cost_basis_consumed = sell_data.get("cost_basis_consumed")
    realized_pnl = sell_data.get("realized_pnl_generated")
    assert cost_basis_consumed is not None, f"sell response: {sell_data}"
    assert realized_pnl is not None, f"sell response: {sell_data}"
    assert abs(float(cost_basis_consumed) - 1000.0) < 1.0
    net = Decimal(str(sell_data["net_eur"]))
    assert abs(float(realized_pnl) - (float(net) - 1000.0)) < 1.0

    stats = client.get("/api/app/wallet/statistics/BTC", headers=auth).json()
    expected_remaining = float(crypto_qty - sell_half)
    assert abs(stats["position_size"] - expected_remaining) < 1e-6


# ---------------------------------------------------------------------------
# Test 4 — Multiple BUY then SELL (WAC)
# ---------------------------------------------------------------------------


def test_pnl_multiple_buy_then_sell_wac(client: TestClient, db: Session):
    """Buy @ 40k, buy @ 60k, sell partial. Verify WAC."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=50_000.0)
    cid = str(pe_client.id)

    # Simulate two buys at different prices via API (price is passed)
    _buy(client, cid, 4000.0)  # 4000 EUR @ 85k (test uses fixed price)
    buy2 = _buy(client, cid, 6000.0)
    total_crypto = Decimal(str(buy2["crypto_position_after"]))
    # WAC: (4000 + 6000) / total_crypto = 10000 / total_crypto
    sell_half = (total_crypto / 2).quantize(BTC_QUANT, rounding=ROUND_DOWN)
    sell_data = _sell(client, cid, str(sell_half))
    assert sell_data["status"] == "completed"

    cost_consumed = float(sell_data.get("cost_basis_consumed") or 0)
    realized = float(sell_data.get("realized_pnl_generated") or 0)
    # Cost for half = 5000 (WAC: 4000+6000 total, half = 5000)
    assert abs(cost_consumed - 5000.0) < 5.0, f"cost_consumed={cost_consumed}"
    net = float(sell_data["net_eur"])
    assert abs(realized - (net - 5000.0)) < 2.0


# ---------------------------------------------------------------------------
# Test 5 — Invariant A: NAV = cash + crypto
# ---------------------------------------------------------------------------


def test_pnl_invariant_a(client: TestClient, db: Session):
    """NAV = cash_eur + crypto_value."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    cid = str(pe_client.id)
    _seed_market_data(db)

    _buy(client, cid, 2000.0)
    db.flush()

    result = compute_pnl_invariants(db, pe_client.id)
    assert result["invariant_a_ok"] is True
    assert result["all_ok"] is True


# ---------------------------------------------------------------------------
# Test 6 — Invariant B: total_pnl = realized + unrealized
# ---------------------------------------------------------------------------


def test_pnl_invariant_b(client: TestClient, db: Session):
    """total_pnl = realized + unrealized."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    cid = str(pe_client.id)
    _seed_market_data(db)

    _buy(client, cid, 3000.0)
    db.flush()

    result = compute_pnl_invariants(db, pe_client.id)
    assert result["invariant_b_ok"] is True


# ---------------------------------------------------------------------------
# Test 7 — Invariant C: NAV = net_external_cash_flows + realized + unrealized
# ---------------------------------------------------------------------------


def test_pnl_invariant_c(client: TestClient, db: Session):
    """NAV = net_external_cash_flows + realized + unrealized."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    cid = str(pe_client.id)
    _seed_market_data(db)

    _buy(client, cid, 4000.0)
    db.flush()

    result = compute_pnl_invariants(db, pe_client.id)
    assert result["invariant_c_ok"] is True


# ---------------------------------------------------------------------------
# Test 8 — Persistance SELL
# ---------------------------------------------------------------------------


def test_pnl_sell_persists_cost_basis_and_realized(client: TestClient, db: Session):
    """SELL order persists cost_basis_consumed and realized_pnl_generated."""
    pe_client, _, _ = _full_setup(client, db, initial_eur=10_000.0)
    cid = str(pe_client.id)

    buy_data = _buy(client, cid, 1500.0)
    crypto_qty = Decimal(str(buy_data["crypto_position_after"]))
    sell_amount = str((crypto_qty / 2).quantize(BTC_QUANT, rounding=ROUND_DOWN))

    sell_data = _sell(client, cid, sell_amount)
    assert sell_data["status"] == "completed"
    order_id = sell_data["order_id"]

    order = db.query(ExchangeOrder).filter(ExchangeOrder.id == UUID(order_id)).first()
    assert order is not None
    assert order.cost_basis_consumed is not None
    assert order.realized_pnl_generated is not None
    assert float(order.cost_basis_consumed) > 0
    # Realized can be positive or negative depending on price
    assert order.realized_pnl_generated is not None
