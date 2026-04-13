"""Wallet Statistics service.

Computes per-asset statistics from exchange_orders, crypto_positions,
market data candles and latest quotes.

Supports optional portfolio scoping:
  - None / "global"  → all orders + crypto_positions  (backward compatible)
  - "direct"         → non-bundle orders + direct atom quantity
  - "bundle"         → bundle orders for a specific portfolio_id + bundle atom quantity
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import (
    MarketDataBar1d,
    MarketDataInstrument,
    MarketDataLatestQuote,
)
from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.exchange.models import CryptoPosition, ExchangeOrder
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur

logger = logging.getLogger(__name__)

D2 = Decimal("0.01")
D8 = Decimal("0.00000001")


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _f2(v: Decimal) -> float:
    return float(v.quantize(D2, rounding=ROUND_HALF_UP))


def _f8(v: Decimal) -> float:
    return float(v.quantize(D8, rounding=ROUND_HALF_UP))


def _resolve_instrument_id(db: Session, provider_symbol: str) -> Optional[int]:
    row = (
        db.query(MarketDataInstrument.id)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    return row[0] if row else None


def _get_live_price_usdt(db: Session, instrument_id: int) -> Optional[Decimal]:
    quote = (
        db.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == instrument_id)
        .first()
    )
    if quote and quote.last_price:
        return Decimal(str(quote.last_price))
    return None


def _compute_volatility_30d(
    db: Session,
    instrument_id: int,
    since: Optional[datetime] = None,
) -> Optional[float]:
    """Annualised 30-day historical volatility from daily close returns.

    When *since* is provided, only candles from that date onwards are used
    (prevents using irrelevant pre-position data).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=35)
    if since is not None and since > cutoff:
        cutoff = since
    rows = (
        db.query(MarketDataBar1d.close)
        .filter(
            MarketDataBar1d.instrument_id == instrument_id,
            MarketDataBar1d.open_time >= cutoff,
        )
        .order_by(MarketDataBar1d.open_time.asc())
        .all()
    )
    closes = [float(r[0]) for r in rows if r[0] and float(r[0]) > 0]
    if len(closes) < 3:
        return None
    log_returns = []
    for i in range(1, len(closes)):
        log_returns.append(math.log(closes[i] / closes[i - 1]))
    if not log_returns:
        return None
    mean = sum(log_returns) / len(log_returns)
    var = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
    daily_vol = math.sqrt(var)
    annual_vol = daily_vol * math.sqrt(365)
    return round(annual_vol, 4)


def _compute_max_drawdown(
    db: Session,
    instrument_id: int,
    since: Optional[datetime] = None,
) -> Optional[float]:
    """Max drawdown from daily close prices since the user opened the position.

    Only considers candles from *since* (first_trade_at) onwards so the
    metric reflects the user's actual position experience, not the asset's
    all-time history.
    """
    filters = [MarketDataBar1d.instrument_id == instrument_id]
    if since is not None:
        filters.append(MarketDataBar1d.open_time >= since)
    rows = (
        db.query(MarketDataBar1d.close)
        .filter(*filters)
        .order_by(MarketDataBar1d.open_time.asc())
        .all()
    )
    closes = [float(r[0]) for r in rows if r[0] and float(r[0]) > 0]
    if len(closes) < 2:
        return None
    peak = closes[0]
    max_dd = 0.0
    for c in closes[1:]:
        if c > peak:
            peak = c
        dd = (c - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 4)


def _get_scoped_position_size(
    db: Session,
    client_id,
    asset: str,
    portfolio_scope: Optional[str],
    portfolio_id: Optional[str],
) -> Decimal:
    """Return position quantity from the correct source based on scope."""
    if portfolio_scope is None or portfolio_scope == "global":
        pos_row = (
            db.query(CryptoPosition)
            .filter(
                CryptoPosition.client_id == client_id,
                CryptoPosition.asset == asset.upper(),
            )
            .first()
        )
        return _dec(pos_row.balance) if pos_row else Decimal("0")

    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.positions.models import PositionAtom

    resolved_pid: Optional[UUID] = None
    if portfolio_scope == "direct":
        from services.portfolio_engine.direct_overlay import ensure_direct_portfolio
        pf = ensure_direct_portfolio(db, client_id)
        resolved_pid = pf.id
    elif portfolio_scope == "bundle" and portfolio_id:
        resolved_pid = UUID(str(portfolio_id))

    if resolved_pid is None:
        return Decimal("0")

    asset_obj = db.query(Asset).filter(Asset.symbol == asset.upper()).first()
    if not asset_obj:
        return Decimal("0")
    instrument = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset_obj.id, Instrument.instrument_type == "spot")
        .first()
    )
    if not instrument:
        return Decimal("0")

    atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == resolved_pid,
            PositionAtom.instrument_id == instrument.id,
            PositionAtom.position_type == "spot",
            PositionAtom.status == "open",
        )
        .first()
    )
    return _dec(atom.quantity) if atom else Decimal("0")


def _apply_scope_filter(q, portfolio_scope: Optional[str], portfolio_id: Optional[str]):
    """Apply scope-based filtering to an ExchangeOrder query.

    Uses metadata_->>'portfolio_scope' as the sole scope discriminator.
    All orders must be tagged via the backfill endpoint before this is used.
    """
    if portfolio_scope is None or portfolio_scope == "global":
        return q

    if portfolio_scope == "direct":
        return q.filter(
            ExchangeOrder.metadata_["portfolio_scope"].astext == "direct",
        )

    if portfolio_scope == "bundle" and portfolio_id:
        return q.filter(
            ExchangeOrder.metadata_["portfolio_scope"].astext == "bundle",
            ExchangeOrder.metadata_["portfolio_id"].astext == str(portfolio_id),
        )

    return q


def build_wallet_statistics(
    db: Session,
    client_id,
    asset: str,
    reference_currency: str = "EUR",
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[str] = None,
) -> dict:
    """Build complete statistics for a single asset position.

    Scope:
      - None / "global" → all orders + crypto_positions (default, backward compatible)
      - "direct"         → non-bundle orders + direct atom quantity
      - "bundle"         → bundle orders for portfolio_id + bundle atom quantity
    """
    use_eur = reference_currency.upper() == "EUR"

    q = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client_id,
            ExchangeOrder.asset == asset.upper(),
            ExchangeOrder.status == "completed",
        )
    )
    q = _apply_scope_filter(q, portfolio_scope, portfolio_id)
    orders = q.order_by(ExchangeOrder.created_at.asc()).all()

    provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset.upper(), f"{asset.upper()}USDT")
    instrument_id = _resolve_instrument_id(db, provider_symbol)

    eurusdt_rate = get_eurusdt_rate(db, strict=False)

    def _to_ref(usdt_price: Decimal) -> Decimal:
        if use_eur:
            return usdt_to_eur(usdt_price, eurusdt_rate)
        return usdt_price

    # ── Current price ───────────────────────────────────────────────
    current_price_usdt = Decimal("0")
    if instrument_id is not None:
        p = _get_live_price_usdt(db, instrument_id)
        if p is not None:
            current_price_usdt = p
    current_price = _to_ref(current_price_usdt)

    # ── Position size (scoped) ──────────────────────────────────────
    position_size = _get_scoped_position_size(
        db, client_id, asset, portfolio_scope, portfolio_id,
    )

    # ── Trade aggregation ────────────────────────────────────────────
    total_bought = Decimal("0")
    total_sold = Decimal("0")
    total_buy_cost = Decimal("0")
    total_sell_revenue = Decimal("0")
    trade_count = len(orders)
    buy_count = 0
    sell_count = 0
    first_trade_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None

    for o in orders:
        amt = _dec(o.amount_crypto)
        price = _dec(o.price)  # execution price in EUR
        if first_trade_at is None:
            first_trade_at = o.created_at
        last_trade_at = o.created_at

        if o.side == "buy":
            buy_count += 1
            total_bought += amt
            total_buy_cost += amt * price
        else:
            sell_count += 1
            total_sold += amt
            # Realized P&L uses net received (amount_to), not gross (amt * price)
            if o.amount_to is not None:
                total_sell_revenue += _dec(o.amount_to)
            else:
                gross = _dec(o.amount_fiat)
                fee = _dec(o.fee_amount) if o.fee_amount else Decimal("0")
                total_sell_revenue += gross - fee

    # ── PRU / Average prices ─────────────────────────────────────────
    avg_buy_price = (total_buy_cost / total_bought) if total_bought > 0 else Decimal("0")
    avg_sell_price = (total_sell_revenue / total_sold) if total_sold > 0 else None

    # execution prices are stored in EUR; convert if user wants USD
    if not use_eur and eurusdt_rate > 0:
        avg_buy_price = avg_buy_price * eurusdt_rate
        if avg_sell_price is not None:
            avg_sell_price = avg_sell_price * eurusdt_rate
        total_buy_cost = total_buy_cost * eurusdt_rate
        total_sell_revenue = total_sell_revenue * eurusdt_rate

    # ── P&L ──────────────────────────────────────────────────────────
    current_value = position_size * current_price
    cost_basis = position_size * avg_buy_price if avg_buy_price > 0 else Decimal("0")
    unrealized_pnl = current_value - cost_basis

    # realized = sell revenue - proportional cost
    if total_sold > 0 and total_bought > 0:
        cost_per_unit = total_buy_cost / total_bought
        realized_pnl = total_sell_revenue - (total_sold * cost_per_unit)
    else:
        realized_pnl = Decimal("0")

    total_pnl = unrealized_pnl + realized_pnl

    # ── Position Quality ─────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    position_age_days = 0
    if first_trade_at:
        ft = first_trade_at
        if ft.tzinfo is None:
            ft = ft.replace(tzinfo=timezone.utc)
        position_age_days = max(0, (now - ft).days)

    break_even_pct: Optional[float] = None
    if avg_buy_price > 0 and current_price > 0:
        break_even_pct = round(
            float((current_price - avg_buy_price) / avg_buy_price * 100), 2
        )

    volatility_30d: Optional[float] = None
    max_drawdown: Optional[float] = None
    if instrument_id is not None:
        volatility_30d = _compute_volatility_30d(db, instrument_id, since=first_trade_at)
        max_drawdown = _compute_max_drawdown(db, instrument_id, since=first_trade_at)

    # portfolio weight: value of this asset / total portfolio value (within scope)
    portfolio_weight: Optional[float] = None
    if current_value > 0:
        if portfolio_scope is None or portfolio_scope == "global":
            all_positions = (
                db.query(CryptoPosition)
                .filter(CryptoPosition.client_id == client_id)
                .all()
            )
            total_portfolio = Decimal("0")
            for p in all_positions:
                ps = ASSET_PROVIDER_SYMBOL_MAP.get(p.asset, f"{p.asset}USDT")
                iid = _resolve_instrument_id(db, ps)
                if iid is not None:
                    p_price_usdt = _get_live_price_usdt(db, iid)
                    if p_price_usdt is not None:
                        total_portfolio += _dec(p.balance) * _to_ref(p_price_usdt)
            if total_portfolio > 0:
                portfolio_weight = round(float(current_value / total_portfolio), 4)
        else:
            portfolio_weight = None

    scope_label = portfolio_scope or "global"
    return {
        "asset": asset.upper(),
        "currency": reference_currency.upper(),
        "current_value": _f2(current_value),
        "position_size": _f8(position_size),
        "average_entry_price": _f2(avg_buy_price),
        "current_price": _f2(current_price),
        "unrealized_pnl": _f2(unrealized_pnl),
        "realized_pnl": _f2(realized_pnl),
        "total_pnl": _f2(total_pnl),
        "first_trade_at": first_trade_at.isoformat() if first_trade_at else None,
        "last_trade_at": last_trade_at.isoformat() if last_trade_at else None,
        "trade_count": trade_count,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_bought": _f8(total_bought),
        "total_sold": _f8(total_sold),
        "avg_buy_price": _f2(avg_buy_price),
        "avg_sell_price": _f2(avg_sell_price) if avg_sell_price is not None else None,
        "position_age_days": position_age_days,
        "break_even_distance_pct": break_even_pct,
        "volatility_30d": volatility_30d,
        "max_drawdown": max_drawdown,
        "portfolio_weight": portfolio_weight,
        "scope": scope_label,
    }
