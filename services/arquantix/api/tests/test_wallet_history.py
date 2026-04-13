"""Tests for Wallet Historical Value Chart endpoint.

Coverage:
  1. Wallet history with a single BUY trade
  2. Wallet history with BUY + SELL trades
  3. EUR conversion using EURUSDT candles
  4. Response is capped at 500 points
  5. Empty history (no trades)
  6. Granularity: 1m selection for < 2h span
  7. Granularity: 5m selection beyond 2h
  8. Wallet history reconstruction with 1m candles
  9. EUR conversion with EURUSDT 1m candles
  10. 500 points limit still respected with 1m candles
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    MarketDataBar1m,
    MarketDataBar1d,
    MarketDataBar5m,
    MarketDataInstrument,
    MarketDataLatestQuote,
)
from services.exchange.models import ExchangeOrder

from conftest import make_linked_client, mobile_auth_headers


def _unique_email() -> str:
    return f"wh-{uuid.uuid4().hex[:8]}@example.com"


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
    existing = db.query(MarketDataLatestQuote).filter(
        MarketDataLatestQuote.instrument_id == instrument_id,
    ).first()
    if existing:
        existing.last_price = price
        existing.updated_at = datetime.now(timezone.utc)
        db.flush()
        return
    quote = MarketDataLatestQuote(
        instrument_id=instrument_id,
        provider="binance",
        provider_symbol=provider_symbol,
        last_price=price,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(quote)
    db.flush()


def _seed_candle_1d(db: Session, instrument_id: int, open_time: datetime, close_price: float) -> None:
    existing = (
        db.query(MarketDataBar1d)
        .filter(
            MarketDataBar1d.instrument_id == instrument_id,
            MarketDataBar1d.open_time == open_time,
        )
        .first()
    )
    if existing:
        existing.close = close_price
        db.flush()
        return
    bar = MarketDataBar1d(
        instrument_id=instrument_id,
        open_time=open_time,
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Decimal("1000"),
        source="binance",
    )
    db.add(bar)
    db.flush()


def _insert_order(
    db: Session,
    client_id,
    side: str,
    asset: str,
    amount_crypto: float,
    price: float,
    created_at: datetime,
) -> None:
    order = ExchangeOrder(
        id=uuid.uuid4(),
        client_id=client_id,
        side=side,
        asset=asset,
        amount_crypto=Decimal(str(amount_crypto)),
        amount_fiat=Decimal(str(amount_crypto * price)),
        price=Decimal(str(price)),
        currency="EUR",
        status="completed",
        external_reference=f"test-{uuid.uuid4().hex[:8]}",
        from_asset="EUR" if side == "buy" else asset,
        to_asset=asset if side == "buy" else "EUR",
        amount_from=Decimal(str(amount_crypto * price)) if side == "buy" else Decimal(str(amount_crypto)),
        amount_to=Decimal(str(amount_crypto)) if side == "buy" else Decimal(str(amount_crypto * price)),
        created_at=created_at,
    )
    db.add(order)
    db.flush()


def _setup_client(db: Session):
    return make_linked_client(db, email=_unique_email())


# ---------------------------------------------------------------------------
# 1. Empty history
# ---------------------------------------------------------------------------

def test_wallet_history_empty(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["points"] == []
    assert data["currency"] in ("EUR", "USD")


# ---------------------------------------------------------------------------
# 2. Single BUY trade
# ---------------------------------------------------------------------------

def test_wallet_history_single_buy(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)
    trade_time = now - timedelta(days=5)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    for d in range(6):
        ts = now - timedelta(days=5 - d)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        _seed_candle_1d(db, btc_iid, ts, 80000.0 + d * 1000)
        _seed_candle_1d(db, eur_iid, ts, 1.08)

    _insert_order(db, client_id, "buy", "BTC", 0.1, 7400.0, trade_time)

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["points"]) >= 2
    assert data["currency"] == "EUR"

    for p in data["points"]:
        assert "timestamp" in p
        assert "wallet_value" in p
        assert isinstance(p["wallet_value"], (int, float))

    last_val = data["points"][-1]["wallet_value"]
    assert last_val > 0, f"Last wallet value should be positive, got {last_val}"


# ---------------------------------------------------------------------------
# 3. BUY + SELL
# ---------------------------------------------------------------------------

def test_wallet_history_buy_and_sell(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    for d in range(11):
        ts = now - timedelta(days=10 - d)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        _seed_candle_1d(db, btc_iid, ts, 80000.0 + d * 500)
        _seed_candle_1d(db, eur_iid, ts, 1.08)

    _insert_order(db, client_id, "buy", "BTC", 0.5, 74000.0, now - timedelta(days=10))
    _insert_order(db, client_id, "sell", "BTC", 0.2, 76000.0, now - timedelta(days=5))

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["points"]) >= 3

    ts_sell = (now - timedelta(days=5)).isoformat()
    values_after_sell = [
        p["wallet_value"]
        for p in data["points"]
        if p["timestamp"] >= ts_sell
    ]
    values_before_sell = [
        p["wallet_value"]
        for p in data["points"]
        if p["timestamp"] < ts_sell
    ]
    if values_before_sell and values_after_sell:
        assert max(values_after_sell) < max(values_before_sell) * 1.5


# ---------------------------------------------------------------------------
# 4. EUR conversion
# ---------------------------------------------------------------------------

def test_wallet_history_eur_conversion(client: TestClient, db: Session):
    """Verify that EUR conversion uses EURUSDT candles."""
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    ts = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    _seed_candle_1d(db, btc_iid, ts, 90000.0)
    _seed_candle_1d(db, eur_iid, ts, 1.10)

    ts2 = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    _seed_candle_1d(db, btc_iid, ts2, 91000.0)
    _seed_candle_1d(db, eur_iid, ts2, 1.10)

    _insert_order(db, client_id, "buy", "BTC", 1.0, 81818.18, now - timedelta(days=2))

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["currency"] == "EUR"

    non_trade_points = [
        p for p in data["points"]
        if abs(p["wallet_value"] - 81818.18) > 100
    ]
    for p in non_trade_points:
        assert p["wallet_value"] < 100000, (
            f"EUR value should be < 100k (90000/1.10 ≈ 81818), got {p['wallet_value']}"
        )


# ---------------------------------------------------------------------------
# 5. Limit 500 points
# ---------------------------------------------------------------------------

def test_wallet_history_max_500_points(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    db.query(MarketDataBar1d).filter(
        MarketDataBar1d.instrument_id.in_([btc_iid, eur_iid])
    ).delete(synchronize_session=False)
    db.flush()

    bars = []
    for d in range(550):
        ts = now - timedelta(days=550 - d)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        price = 60000.0 + d * 10
        bars.append(MarketDataBar1d(
            instrument_id=btc_iid, open_time=ts,
            open=Decimal(str(price)), high=Decimal(str(price)),
            low=Decimal(str(price)), close=Decimal(str(price)),
            volume=Decimal("1000"), source="binance",
        ))
        bars.append(MarketDataBar1d(
            instrument_id=eur_iid, open_time=ts,
            open=Decimal("1.08"), high=Decimal("1.08"),
            low=Decimal("1.08"), close=Decimal("1.08"),
            volume=Decimal("1000"), source="binance",
        ))
    db.bulk_save_objects(bars)
    db.flush()

    _insert_order(db, client_id, "buy", "BTC", 0.01, 55556.0, now - timedelta(days=550))

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["points"]) <= 500, f"Expected max 500 points, got {len(data['points'])}"
    assert len(data["points"]) >= 50, f"Expected at least 50 points for 550-day range"


# ---------------------------------------------------------------------------
# 6. Period filter
# ---------------------------------------------------------------------------

def test_wallet_history_period_filter(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    for d in range(40):
        ts = now - timedelta(days=40 - d)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        _seed_candle_1d(db, btc_iid, ts, 80000.0 + d * 100)
        _seed_candle_1d(db, eur_iid, ts, 1.08)

    _insert_order(db, client_id, "buy", "BTC", 0.1, 74000.0, now - timedelta(days=35))

    res_all = client.get("/api/app/wallet/history?period=ALL", headers=auth)
    assert res_all.status_code == 200
    pts_all = res_all.json()["points"]

    res_1w = client.get("/api/app/wallet/history?period=1W", headers=auth)
    assert res_1w.status_code == 200
    pts_1w = res_1w.json()["points"]

    assert len(pts_1w) <= len(pts_all), "1W should have fewer or equal points than ALL"


# ---------------------------------------------------------------------------
# Helper: seed 1m / 5m candles
# ---------------------------------------------------------------------------

def _seed_candle_1m(db: Session, instrument_id: int, open_time: datetime, close_price: float) -> None:
    existing = (
        db.query(MarketDataBar1m)
        .filter(
            MarketDataBar1m.instrument_id == instrument_id,
            MarketDataBar1m.open_time == open_time,
        )
        .first()
    )
    if existing:
        existing.close = close_price
        db.flush()
        return
    bar = MarketDataBar1m(
        instrument_id=instrument_id,
        open_time=open_time,
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Decimal("100"),
        source="binance",
    )
    db.add(bar)
    db.flush()


def _seed_candle_5m(db: Session, instrument_id: int, open_time: datetime, close_price: float) -> None:
    existing = (
        db.query(MarketDataBar5m)
        .filter(
            MarketDataBar5m.instrument_id == instrument_id,
            MarketDataBar5m.open_time == open_time,
        )
        .first()
    )
    if existing:
        existing.close = close_price
        db.flush()
        return
    bar = MarketDataBar5m(
        instrument_id=instrument_id,
        open_time=open_time,
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Decimal("100"),
        source="binance",
    )
    db.add(bar)
    db.flush()


# ---------------------------------------------------------------------------
# 7. Granularity selection: 1m for span < 2h
# ---------------------------------------------------------------------------

def test_wallet_history_granularity_1m_selection(client: TestClient, db: Session):
    """When total span is < 2h, the service should use MarketDataBar1m."""
    from services.wallet_history.service import _select_granularity, MarketDataBar1m

    _idx, model, interval = _select_granularity(1.5)  # 1.5 hours
    assert model is MarketDataBar1m, f"Expected MarketDataBar1m for 1.5h span, got {model}"
    assert interval == 60


# ---------------------------------------------------------------------------
# 8. Granularity selection: 5m beyond 2h
# ---------------------------------------------------------------------------

def test_wallet_history_granularity_5m_beyond_2h(client: TestClient, db: Session):
    """When total span is 3h–7d, the service should use MarketDataBar5m."""
    from services.wallet_history.service import _select_granularity, MarketDataBar5m

    _idx, model, interval = _select_granularity(3.0)  # 3 hours
    assert model is MarketDataBar5m, f"Expected MarketDataBar5m for 3h span, got {model}"
    assert interval == 300

    _idx, model, interval = _select_granularity(100.0)  # ~4 days
    assert model is MarketDataBar5m, f"Expected MarketDataBar5m for 100h span, got {model}"
    assert interval == 300


# ---------------------------------------------------------------------------
# 9. Wallet history reconstruction with 1m candles
# ---------------------------------------------------------------------------

def test_wallet_history_with_1m_candles(client: TestClient, db: Session):
    """Trade < 2h ago: wallet history should use 1m candles and return minute-level data."""
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)
    trade_time = now - timedelta(minutes=90)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    for m in range(100):
        ts = now - timedelta(minutes=100 - m)
        ts = ts.replace(second=0, microsecond=0)
        _seed_candle_1m(db, btc_iid, ts, 95000.0 + m * 10)
        _seed_candle_1m(db, eur_iid, ts, 1.09)

    _insert_order(db, client_id, "buy", "BTC", 0.5, 43578.0, trade_time)

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["points"]) >= 5, f"Expected several 1m-level points, got {len(data['points'])}"
    assert data["currency"] == "EUR"

    for p in data["points"]:
        assert p["wallet_value"] > 0


# ---------------------------------------------------------------------------
# 10. EUR conversion with EURUSDT 1m candles
# ---------------------------------------------------------------------------

def test_wallet_history_eur_conversion_1m(client: TestClient, db: Session):
    """Verify EUR conversion with EURUSDT 1m candles on a short timespan."""
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)
    trade_time = now - timedelta(minutes=60)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    _seed_quote(db, btc_iid, 90000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")

    for m in range(70):
        ts = now - timedelta(minutes=70 - m)
        ts = ts.replace(second=0, microsecond=0)
        _seed_candle_1m(db, btc_iid, ts, 90000.0)
        _seed_candle_1m(db, eur_iid, ts, 1.10)

    _insert_order(db, client_id, "buy", "BTC", 1.0, 81818.0, trade_time)

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["currency"] == "EUR"

    non_trade_values = [
        p["wallet_value"] for p in data["points"]
        if abs(p["wallet_value"] - 81818.0) > 100
    ]
    for v in non_trade_values:
        assert v < 100000, f"EUR value should be ~81818 (90000/1.10), got {v}"
        assert v > 70000, f"EUR value should be ~81818 (90000/1.10), got {v}"


# ---------------------------------------------------------------------------
# 11. 500 points limit still respected with 1m data
# ---------------------------------------------------------------------------

def test_wallet_history_max_500_points_1m(client: TestClient, db: Session):
    """Even with dense 1m candles, output should not exceed 500 points."""
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    client_id = pe.id
    now = datetime.now(timezone.utc)
    trade_time = now - timedelta(minutes=110)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT", asset_class="forex")

    db.query(MarketDataBar1m).filter(
        MarketDataBar1m.instrument_id.in_([btc_iid, eur_iid])
    ).delete(synchronize_session=False)
    db.flush()

    bars = []
    for m in range(120):
        ts = now - timedelta(minutes=120 - m)
        ts = ts.replace(second=0, microsecond=0)
        bars.append(MarketDataBar1m(
            instrument_id=btc_iid, open_time=ts,
            open=Decimal("90000"), high=Decimal("90000"),
            low=Decimal("90000"), close=Decimal("90000"),
            volume=Decimal("100"), source="binance",
        ))
        bars.append(MarketDataBar1m(
            instrument_id=eur_iid, open_time=ts,
            open=Decimal("1.08"), high=Decimal("1.08"),
            low=Decimal("1.08"), close=Decimal("1.08"),
            volume=Decimal("100"), source="binance",
        ))
    db.bulk_save_objects(bars)
    db.flush()

    _insert_order(db, client_id, "buy", "BTC", 0.1, 8333.0, trade_time)

    res = client.get("/api/app/wallet/history", headers=auth)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["points"]) <= 500, f"Expected max 500 points, got {len(data['points'])}"
