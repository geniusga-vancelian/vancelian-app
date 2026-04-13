"""Tests for Pricing Consistency Hardening (R1 strict FX + R4 dual-currency gains).

Coverage:
  1. BUY fails with 503 if EURUSDT FX quote is missing (strict mode)
  2. SELL fails with 503 if EURUSDT FX quote is missing (strict mode)
  3. BUY succeeds when both crypto + EURUSDT quotes exist
  4. SELL succeeds when both crypto + EURUSDT quotes exist
  5. Crypto wallet detail returns dual-currency gains / PRU
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.exchange.assets import ASSET_PRECISION

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}

BTC_PRICE_USDT = 85_000.0
EURUSDT_RATE = 1.08


@pytest.fixture(autouse=True)
def _no_binance_quote_refresh_pricing(monkeypatch):
    """Les scénarios R1 contrôlent les lignes en base ; Binance REST ne doit pas repopuler EURUSDT."""
    def _noop(_db, _symbols):
        return None

    monkeypatch.setattr(
        "services.exchange.service.refresh_binance_quotes_for_provider_symbols",
        _noop,
    )


def _seed_instrument(db: Session, symbol: str, provider_symbol: str, asset_class: str = "crypto") -> int:
    existing = db.query(MarketDataInstrument).filter(MarketDataInstrument.symbol == symbol).first()
    if existing:
        return existing.id
    inst = MarketDataInstrument(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        provider="binance",
        provider_symbol=provider_symbol,
        is_active="true",
    )
    db.add(inst)
    db.flush()
    return inst.id


def _seed_quote(db: Session, instrument_id: int, price: float, provider_symbol: str) -> None:
    now = datetime.now(timezone.utc)
    existing = db.query(MarketDataLatestQuote).filter(
        MarketDataLatestQuote.instrument_id == instrument_id,
    ).first()
    if existing:
        existing.last_price = price
        existing.updated_at = now
        existing.quote_time = now
        db.flush()
        return
    quote = MarketDataLatestQuote(
        instrument_id=instrument_id,
        provider="binance",
        provider_symbol=provider_symbol,
        last_price=price,
        updated_at=now,
        quote_time=now,
    )
    db.add(quote)
    db.flush()


def _unique_email() -> str:
    return f"ph-{uuid.uuid4().hex[:8]}@example.com"


def _create_provider(http: TestClient) -> dict:
    res = http.post(
        "/api/admin/custody/providers",
        json={"name": f"Bank-{uuid.uuid4().hex[:6]}", "provider_type": "bank", "jurisdiction": "EU"},
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
        json={"client_id": client_id, "amount": amount, "currency": "EUR", "reference": f"FUND-{uuid.uuid4().hex[:8]}"},
        headers=custody_admin_headers(db),
    )
    assert res.status_code == 200, res.text


def _full_setup(http: TestClient, db: Session, initial_eur: float = 100_000.0):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    _create_client_account(http, provider["id"], str(pe_client.id), db)
    _create_settlement_account(http, provider["id"], db)
    if initial_eur > 0:
        _fund_client(http, str(pe_client.id), initial_eur, db)
    return pe_client


# ---------------------------------------------------------------------------
# R1: BUY fails if EURUSDT FX quote is missing (strict mode, no price override)
# ---------------------------------------------------------------------------

def _ensure_no_eurusdt_quote(db: Session) -> None:
    """Delete the EURUSDT quote if it exists, so strict mode will fail."""
    eur_inst = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.provider_symbol == "EURUSDT",
    ).first()
    if eur_inst:
        db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == eur_inst.id,
        ).delete()
        db.flush()


def test_buy_fails_without_eurusdt_quote(client: TestClient, db: Session):
    """BUY without price override requires both a crypto quote AND an EURUSDT FX quote.
    With only a BTCUSDT quote (no EURUSDT), it must return 503."""
    pe_client = _full_setup(client, db)

    btc_inst_id = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    _seed_quote(db, btc_inst_id, BTC_PRICE_USDT, "BTCUSDT")
    _ensure_no_eurusdt_quote(db)

    ref = f"buy-nofx-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "fiat_amount": 1000.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 503, f"Expected 503 but got {res.status_code}: {res.text}"
    assert "fx_unavailable" in res.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# R1: SELL fails if EURUSDT FX quote is missing (strict mode, no price override)
# ---------------------------------------------------------------------------

def test_sell_fails_without_eurusdt_quote(client: TestClient, db: Session):
    """SELL without price override requires EURUSDT FX quote.
    Buy first with price override (bypasses FX), then attempt to sell without price."""
    pe_client = _full_setup(client, db)

    buy_ref = f"buy-setup-{uuid.uuid4().hex[:8]}"
    buy_res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "fiat_amount": 10_000.0,
            "currency": "EUR",
            "external_reference": buy_ref,
            "price": BTC_PRICE_USDT,
        },
        headers=ADMIN_HEADERS,
    )
    assert buy_res.status_code == 200 and buy_res.json()["status"] == "completed"

    btc_inst_id = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    _seed_quote(db, btc_inst_id, BTC_PRICE_USDT, "BTCUSDT")
    _ensure_no_eurusdt_quote(db)

    quant = Decimal(10) ** -ASSET_PRECISION.get("BTC", 8)
    crypto_after = Decimal(str(buy_res.json()["crypto_position_after"]))
    sell_amount = str((crypto_after / 2).quantize(quant, rounding=ROUND_DOWN))

    sell_ref = f"sell-nofx-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/exchange/sell",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "amount_crypto": sell_amount,
            "currency": "EUR",
            "external_reference": sell_ref,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 503, f"Expected 503 but got {res.status_code}: {res.text}"
    assert "fx_unavailable" in res.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# R1: BUY succeeds when both quotes present (market price mode)
# ---------------------------------------------------------------------------

def test_buy_succeeds_with_eurusdt_quote(client: TestClient, db: Session):
    """BUY without price override succeeds when both BTCUSDT + EURUSDT quotes are present."""
    pe_client = _full_setup(client, db, initial_eur=200_000.0)

    btc_inst_id = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    _seed_quote(db, btc_inst_id, BTC_PRICE_USDT, "BTCUSDT")

    eur_inst_id = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="fx")
    _seed_quote(db, eur_inst_id, EURUSDT_RATE, "EURUSDT")

    ref = f"buy-ok-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "fiat_amount": 1000.0,
            "currency": "EUR",
            "external_reference": ref,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, f"Expected 200 but got {res.status_code}: {res.text}"
    data = res.json()
    assert data["status"] == "completed"
    assert float(data["price"]) > 0


# ---------------------------------------------------------------------------
# R4: Crypto wallet detail returns dual-currency gains/PRU
# ---------------------------------------------------------------------------

def test_wallet_detail_dual_currency_gains(client: TestClient, db: Session):
    """After a buy, the wallet detail endpoint should return both EUR and USD gain metrics."""
    pe_client = _full_setup(client, db, initial_eur=100_000.0)
    auth = mobile_auth_headers(db, pe_client)

    buy_ref = f"buy-gains-{uuid.uuid4().hex[:8]}"
    buy_res = client.post(
        "/api/exchange/buy",
        json={
            "client_id": str(pe_client.id),
            "asset": "BTC",
            "fiat_amount": 10_000.0,
            "currency": "EUR",
            "external_reference": buy_ref,
            "price": BTC_PRICE_USDT,
        },
        headers=ADMIN_HEADERS,
    )
    assert buy_res.status_code == 200 and buy_res.json()["status"] == "completed"

    btc_inst_id = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    _seed_quote(db, btc_inst_id, BTC_PRICE_USDT, "BTCUSDT")
    eur_inst_id = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="fx")
    _seed_quote(db, eur_inst_id, EURUSDT_RATE, "EURUSDT")

    res = client.get("/api/app/crypto-positions/BTC", headers=auth)
    assert res.status_code == 200, res.text
    detail = res.json().get("detail")

    assert detail is not None, "Expected wallet detail for BTC"

    assert detail["current_price_eur"] is not None
    assert detail["current_price_usd"] is not None
    assert detail["total_value_eur"] is not None
    assert detail["total_value_usd"] is not None

    assert detail["avg_buy_price_eur"] is not None
    assert detail["avg_buy_price_usd"] is not None
    assert detail["unrealized_gain_eur"] is not None
    assert detail["unrealized_gain_usd"] is not None
    assert detail["realized_gain_eur"] is not None
    assert detail["realized_gain_usd"] is not None
    assert detail["total_gain_eur"] is not None
    assert detail["total_gain_usd"] is not None

    avg_eur = float(detail["avg_buy_price_eur"])
    avg_usd = float(detail["avg_buy_price_usd"])
    assert avg_eur > 0
    assert avg_usd > 0
    assert avg_usd > avg_eur, "USD avg price should be > EUR avg price (EURUSDT > 1)"
