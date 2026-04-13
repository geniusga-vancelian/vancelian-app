"""Tests for Wallet Statistics endpoint.

Coverage:
  1. Statistics with no trades (empty)
  2. Statistics with a single BUY
  3. Statistics with BUY + SELL (realized P&L)
  4. Trading activity metrics
  5. Risk metrics (volatility, drawdown)
  6. Portfolio weight calculation
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    MarketDataBar1d,
    MarketDataInstrument,
    MarketDataLatestQuote,
)
from services.exchange.models import CryptoPosition, ExchangeOrder

from conftest import make_linked_client, mobile_auth_headers


def _unique_email() -> str:
    return f"ws-{uuid.uuid4().hex[:8]}@example.com"


def _setup_client(db: Session):
    return make_linked_client(db, email=_unique_email())


def _seed_instrument(db: Session, symbol: str, provider_symbol: str) -> int:
    existing = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.symbol == symbol,
    ).first()
    if existing:
        return existing.id
    inst = MarketDataInstrument(
        symbol=symbol,
        name=symbol,
        asset_class="crypto",
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
        existing.high = close_price * 1.02
        existing.low = close_price * 0.98
        db.flush()
        return
    bar = MarketDataBar1d(
        instrument_id=instrument_id,
        open_time=open_time,
        open=close_price,
        high=close_price * 1.02,
        low=close_price * 0.98,
        close=close_price,
        volume=Decimal("1000"),
        source="binance",
    )
    db.add(bar)
    db.flush()


def _seed_position(db: Session, client_id, asset: str, balance: float) -> None:
    existing = db.query(CryptoPosition).filter(
        CryptoPosition.client_id == client_id,
        CryptoPosition.asset == asset,
    ).first()
    if existing:
        existing.balance = Decimal(str(balance))
        existing.available_balance = Decimal(str(balance))
        db.flush()
        return
    pos = CryptoPosition(
        id=uuid.uuid4(),
        client_id=client_id,
        asset=asset,
        balance=Decimal(str(balance)),
        available_balance=Decimal(str(balance)),
    )
    db.add(pos)
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


# ---------------------------------------------------------------------------
# 1. Empty statistics (no trades)
# ---------------------------------------------------------------------------

def test_wallet_statistics_no_trades(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert data["asset"] == "BTC"
    assert data["trade_count"] == 0
    assert data["current_value"] == 0
    assert data["position_size"] == 0
    assert data["total_pnl"] == 0


# ---------------------------------------------------------------------------
# 2. Statistics with a single BUY
# ---------------------------------------------------------------------------

def test_wallet_statistics_single_buy(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 85000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")
    _seed_position(db, cid, "BTC", 0.01)
    _insert_order(db, cid, "buy", "BTC", 0.01, 62000.0, now - timedelta(hours=1))
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["asset"] == "BTC"
    assert data["trade_count"] == 1
    assert data["buy_count"] == 1
    assert data["sell_count"] == 0
    assert data["position_size"] == 0.01
    assert data["average_entry_price"] == 62000.0
    assert data["total_bought"] == 0.01
    assert data["total_sold"] == 0
    assert data["current_price"] > 0
    assert data["current_value"] > 0
    assert data["first_trade_at"] is not None
    assert data["portfolio_weight"] is not None


# ---------------------------------------------------------------------------
# 3. Statistics with BUY + SELL (realized P&L)
# ---------------------------------------------------------------------------

def test_wallet_statistics_buy_sell(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 85000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")
    _seed_position(db, cid, "BTC", 0.005)

    _insert_order(db, cid, "buy", "BTC", 0.01, 60000.0, now - timedelta(days=5))
    _insert_order(db, cid, "sell", "BTC", 0.005, 65000.0, now - timedelta(days=1))
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["trade_count"] == 2
    assert data["buy_count"] == 1
    assert data["sell_count"] == 1
    assert data["total_bought"] == 0.01
    assert data["total_sold"] == 0.005
    assert data["avg_sell_price"] == 65000.0
    # Realized P&L: sell revenue (0.005*65000=325) - cost (0.005*60000=300) = 25 EUR
    assert data["realized_pnl"] == 25.0
    assert data["position_age_days"] >= 4


# ---------------------------------------------------------------------------
# 4. Risk metrics (volatility, drawdown from candles)
# ---------------------------------------------------------------------------

def test_wallet_statistics_risk_metrics(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 85000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")
    _seed_position(db, cid, "BTC", 0.01)
    _insert_order(db, cid, "buy", "BTC", 0.01, 62000.0, now - timedelta(days=30))

    # Seed 30 days of candles for volatility + drawdown
    for i in range(30):
        price = 80000 + (i * 500) - (1000 if i % 5 == 0 else 0)
        _seed_candle_1d(db, btc_iid, now - timedelta(days=30 - i), price)
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["volatility_30d"] is not None
    assert isinstance(data["volatility_30d"], float)
    assert data["max_drawdown"] is not None
    assert data["max_drawdown"] < 0
    assert data["break_even_distance_pct"] is not None


# ---------------------------------------------------------------------------
# 5. Portfolio weight with multiple positions
# ---------------------------------------------------------------------------

def test_wallet_statistics_portfolio_weight(client: TestClient, db: Session):
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eth_iid = _seed_instrument(db, "ETHUSDT", "ETHUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 80000.0, "BTCUSDT")
    _seed_quote(db, eth_iid, 3000.0, "ETHUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")

    _seed_position(db, cid, "BTC", 0.01)
    _seed_position(db, cid, "ETH", 1.0)
    _insert_order(db, cid, "buy", "BTC", 0.01, 60000.0, now - timedelta(days=2))
    _insert_order(db, cid, "buy", "ETH", 1.0, 2500.0, now - timedelta(days=2))
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    assert data["portfolio_weight"] is not None
    assert 0 < data["portfolio_weight"] < 1


# ---------------------------------------------------------------------------
# 6. Max drawdown scoped to position (ignores pre-trade history)
# ---------------------------------------------------------------------------

def test_wallet_statistics_drawdown_scoped_to_position(client: TestClient, db: Session):
    """Max drawdown must only consider candles since the user's first trade.

    Old bug: the entire asset price history was used, so a crash months
    before the user even bought would show up as *their* max drawdown.
    """
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 85000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")
    _seed_position(db, cid, "BTC", 0.01)

    # User bought 5 days ago
    _insert_order(db, cid, "buy", "BTC", 0.01, 62000.0, now - timedelta(days=5))

    # Seed a catastrophic -90% crash 200 days ago — must NOT count
    _seed_candle_1d(db, btc_iid, now - timedelta(days=200), 90000.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=199), 9000.0)

    # Seed gentle candles during position period (last 5 days)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=5), 84000.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=4), 83500.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=3), 84200.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=2), 83800.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=1), 85000.0)
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    # Without fix: max_drawdown would be ~ -90% (90k→9k crash)
    # With fix: drawdown is scoped to the last 5 days and must be > -50%
    assert data["max_drawdown"] is not None
    assert data["max_drawdown"] > -0.50, (
        f"Max drawdown should exclude pre-trade crash, got {data['max_drawdown']}"
    )


# ---------------------------------------------------------------------------
# 7. Recent single trade: drawdown None when < 2 candles since trade
# ---------------------------------------------------------------------------

def test_wallet_statistics_recent_trade_no_drawdown(client: TestClient, db: Session):
    """A position opened today with no daily candles should return None drawdown."""
    pe = _setup_client(db)
    auth = mobile_auth_headers(db, pe)
    cid = pe.id
    now = datetime.now(timezone.utc)

    btc_iid = _seed_instrument(db, "BTCUSDT", "BTCUSDT")
    eur_iid = _seed_instrument(db, "EURUSDT", "EURUSDT")
    _seed_quote(db, btc_iid, 85000.0, "BTCUSDT")
    _seed_quote(db, eur_iid, 1.10, "EURUSDT")
    _seed_position(db, cid, "BTC", 0.01)

    # Trade just happened, only old candles exist (before trade)
    _insert_order(db, cid, "buy", "BTC", 0.01, 62000.0, now - timedelta(hours=1))
    _seed_candle_1d(db, btc_iid, now - timedelta(days=30), 70000.0)
    _seed_candle_1d(db, btc_iid, now - timedelta(days=29), 35000.0)
    db.flush()

    res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
    assert res.status_code == 200
    data = res.json()

    # No daily candles since the trade → drawdown should be None
    assert data["max_drawdown"] is None
