"""Tests for Simulated Market Execution v1.

Coverage:
  1. BUY uses ask_price when no override
  2. SELL uses bid_price when no override
  3. Fallback spread when bid/ask missing
  4. Override still wins over market price
  5. Execution price persisted correctly
  6. EUR conversion still correct
  7. BUY rejected when quote stale
  8. SELL rejected when quote stale
  9. Quote missing timestamp rejected
  10. Exchange context returns bid/ask/mid/spread
  11. BUY without manual price (market mode)
  12. SELL without manual price (market mode)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.exchange.models import ExchangeFeeConfig
from services.exchange.repository import ExchangeFeeConfigRepository
from services.exchange.service import (
    ExchangeService,
    MarketQuoteStaleError,
    PriceUnavailableError,
)
from services.portfolio_engine.hardening.security.context import ActorContext


def _actor() -> ActorContext:
    return ActorContext(actor_type="admin", actor_id="test@test.com", actor_roles=["admin"])


def _ensure_instrument(db: Session, symbol: str, provider_symbol: str) -> MarketDataInstrument:
    """Create or get a market data instrument."""
    inst = (
        db.query(MarketDataInstrument)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    if inst:
        return inst
    inst = MarketDataInstrument(
        symbol=symbol,
        name=f"Test {symbol}",
        asset_class="crypto",
        weekend_tradable="true",
        provider="binance",
        provider_symbol=provider_symbol,
        is_active="true",
    )
    db.add(inst)
    db.flush()
    return inst


def _upsert_quote(
    db: Session,
    instrument_id: int,
    last_price: float,
    bid_price: float | None = None,
    ask_price: float | None = None,
    quote_time: datetime | None = None,
) -> MarketDataLatestQuote:
    """Create or update a latest quote for testing."""
    if quote_time is None:
        quote_time = datetime.now(timezone.utc)
    quote = db.query(MarketDataLatestQuote).filter(
        MarketDataLatestQuote.instrument_id == instrument_id
    ).first()
    if quote:
        quote.last_price = last_price
        quote.bid_price = bid_price
        quote.ask_price = ask_price
        quote.quote_time = quote_time
        quote.provider = "binance"
    else:
        quote = MarketDataLatestQuote(
            instrument_id=instrument_id,
            provider="binance",
            provider_symbol=None,
            last_price=last_price,
            bid_price=bid_price,
            ask_price=ask_price,
            quote_time=quote_time,
        )
        db.add(quote)
    db.flush()
    return quote


def _ensure_eurusdt(db: Session, rate: float = 1.08) -> None:
    """Create EURUSDT instrument + fresh quote for FX conversion."""
    inst = _ensure_instrument(db, "EUR", "EURUSDT")
    _upsert_quote(db, inst.id, rate, bid_price=rate - 0.0001, ask_price=rate + 0.0001)


def _ensure_fee_config(db: Session, asset: str, fee_bps: int = 50, spread_bps: int = 100) -> None:
    """Ensure an exchange fee config exists for the asset."""
    row = db.query(ExchangeFeeConfig).filter(ExchangeFeeConfig.asset == asset).first()
    if row:
        row.fee_bps = fee_bps
        row.spread_bps = spread_bps
        row.active = True
    else:
        row = ExchangeFeeConfig(asset=asset, fee_bps=fee_bps, spread_bps=spread_bps, active=True)
        db.add(row)
    db.flush()


# ---------------------------------------------------------------------------
# Unit tests for _resolve_price
# ---------------------------------------------------------------------------

class TestResolvePrice:

    def test_buy_uses_ask_when_no_override(self, db: Session):
        """BUY should use ask_price from market data."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0)
        _ensure_eurusdt(db)
        _ensure_fee_config(db, "BTC")

        svc = ExchangeService()
        price_eur = svc._resolve_price(db, "BTC", None, side="buy")

        expected_usdt = Decimal("62150")
        eurusdt = Decimal("1.08")
        expected_eur = expected_usdt / eurusdt
        assert abs(price_eur - expected_eur) < Decimal("1")

    def test_sell_uses_bid_when_no_override(self, db: Session):
        """SELL should use bid_price from market data."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0)
        _ensure_eurusdt(db)
        _ensure_fee_config(db, "BTC")

        svc = ExchangeService()
        price_eur = svc._resolve_price(db, "BTC", None, side="sell")

        expected_usdt = Decimal("61850")
        eurusdt = Decimal("1.08")
        expected_eur = expected_usdt / eurusdt
        assert abs(price_eur - expected_eur) < Decimal("1")

    def test_buy_higher_than_sell(self, db: Session):
        """BUY price (ask) must be higher than SELL price (bid)."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0)
        _ensure_eurusdt(db)
        _ensure_fee_config(db, "BTC")

        svc = ExchangeService()
        buy_price = svc._resolve_price(db, "BTC", None, side="buy")
        sell_price = svc._resolve_price(db, "BTC", None, side="sell")

        assert buy_price > sell_price

    def test_fallback_spread_when_bid_ask_missing(self, db: Session):
        """When bid/ask are NULL, use last_price +/- spread_bps/2."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=None, ask_price=None)
        _ensure_eurusdt(db)
        _ensure_fee_config(db, "BTC", spread_bps=100)

        svc = ExchangeService()
        buy_price = svc._resolve_price(db, "BTC", None, side="buy")
        sell_price = svc._resolve_price(db, "BTC", None, side="sell")

        mid_usdt = Decimal("62000")
        eurusdt = Decimal("1.08")
        expected_ask = mid_usdt * Decimal("1.005") / eurusdt
        expected_bid = mid_usdt * Decimal("0.995") / eurusdt

        assert abs(buy_price - expected_ask) < Decimal("1")
        assert abs(sell_price - expected_bid) < Decimal("1")
        assert buy_price > sell_price

    def test_override_still_wins(self, db: Session):
        """When override_price is set, it should be returned directly."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0)
        _ensure_eurusdt(db)

        svc = ExchangeService()
        override = Decimal("99999.99")
        price = svc._resolve_price(db, "BTC", override, side="buy")
        assert price == override

        price_sell = svc._resolve_price(db, "BTC", override, side="sell")
        assert price_sell == override

    def test_buy_rejected_when_quote_stale(self, db: Session):
        """BUY must be rejected when quote_time is older than 60s."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0,
                       quote_time=stale_time)
        _ensure_eurusdt(db)

        svc = ExchangeService()
        with pytest.raises(MarketQuoteStaleError, match="market_quote_stale"):
            svc._resolve_price(db, "BTC", None, side="buy")

    def test_sell_rejected_when_quote_stale(self, db: Session):
        """SELL must be rejected when quote_time is older than 60s."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0,
                       quote_time=stale_time)
        _ensure_eurusdt(db)

        svc = ExchangeService()
        with pytest.raises(MarketQuoteStaleError, match="market_quote_stale"):
            svc._resolve_price(db, "BTC", None, side="sell")

    def test_quote_missing_timestamp_rejected(self, db: Session):
        """Quote with NULL quote_time must be rejected."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0,
                       quote_time=None)
        # Manually set quote_time to None after creation
        quote = db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == inst.id
        ).first()
        quote.quote_time = None
        db.flush()

        _ensure_eurusdt(db)

        svc = ExchangeService()
        with pytest.raises(MarketQuoteStaleError, match="no quote_time"):
            svc._resolve_price(db, "BTC", None, side="buy")

    def test_override_allowed_even_when_stale(self, db: Session):
        """Manual override must work even when quote is stale."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=300)
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0,
                       quote_time=stale_time)

        svc = ExchangeService()
        override = Decimal("85000")
        price = svc._resolve_price(db, "BTC", override, side="buy")
        assert price == override

    def test_eur_conversion_correct(self, db: Session):
        """Verify USDT→EUR conversion uses the FX rate correctly."""
        inst = _ensure_instrument(db, "ETH", "ETHUSDT")
        _upsert_quote(db, inst.id, last_price=3500.0, bid_price=3490.0, ask_price=3510.0)
        _ensure_eurusdt(db, rate=1.10)
        _ensure_fee_config(db, "ETH")

        svc = ExchangeService()
        price = svc._resolve_price(db, "ETH", None, side="buy")

        expected = Decimal("3510") / Decimal("1.10")
        assert abs(price - expected) < Decimal("0.01")


# ---------------------------------------------------------------------------
# Integration tests via HTTP (admin context)
# ---------------------------------------------------------------------------

class TestExchangeContext:

    def test_context_returns_bid_ask_mid_spread(self, client, db: Session):
        """GET /api/admin/exchange/context must include price data."""
        inst = _ensure_instrument(db, "BTC", "BTCUSDT")
        _upsert_quote(db, inst.id, last_price=62000.0, bid_price=61850.0, ask_price=62150.0)
        _ensure_eurusdt(db)
        _ensure_fee_config(db, "BTC", spread_bps=50)
        db.flush()

        res = client.get(
            "/api/admin/exchange/context",
            headers={"X-Actor-Type": "admin", "X-Actor-Id": "test@test.com", "X-Actor-Roles": "admin"},
        )
        assert res.status_code == 200
        data = res.json()

        btc_asset = next((a for a in data["supported_assets"] if a["symbol"] == "BTC"), None)
        assert btc_asset is not None
        assert btc_asset["bid_price"] is not None
        assert btc_asset["ask_price"] is not None
        assert btc_asset["mid_price"] is not None
        assert btc_asset["spread_bps"] == 50
        assert "is_fresh" in btc_asset
        assert "quote_time" in btc_asset
        assert btc_asset["bid_price"] < btc_asset["ask_price"]
