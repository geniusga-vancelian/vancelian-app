"""Wallet Historical Value reconstruction service.

Rebuilds wallet_value(t) = Σ position_asset_i(t) × price_asset_i(t)
from exchange_orders + OHLC candles + FX history.

Supports optional portfolio scoping:
  - None / "global"  → all orders (backward compatible)
  - "direct"         → non-bundle orders only
  - "bundle"         → bundle orders for a specific portfolio_id
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import (
    MarketDataBar1m,
    MarketDataBar1d,
    MarketDataBar1h,
    MarketDataBar4h,
    MarketDataBar5m,
    MarketDataInstrument,
    MarketDataLatestQuote,
)
from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.exchange.models import ExchangeOrder
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur

logger = logging.getLogger(__name__)

MAX_POINTS = 500
EURUSDT_SYMBOL = "EURUSDT"

_GRANULARITY_CONFIG = [
    # (max_age_hours, bar_model, interval_seconds)
    (2, MarketDataBar1m, 60),           # 0–2h      → 1m
    (168, MarketDataBar5m, 300),        # 2h–7d     → 5m
    (720, MarketDataBar1h, 3600),       # 7d–30d    → 1h
    (2880, MarketDataBar4h, 14400),     # 30d–120d  → 4h
    (None, MarketDataBar1d, 86400),     # >120d     → 1d
]


def _select_granularity(span_hours: float) -> tuple[int, object, int]:
    """Pick the candle table and interval for the given time span.

    Returns (config_index, bar_model, interval_seconds).
    """
    for idx, (max_h, model, interval) in enumerate(_GRANULARITY_CONFIG):
        if max_h is None or span_hours <= max_h:
            return idx, model, interval
    last = len(_GRANULARITY_CONFIG) - 1
    return last, _GRANULARITY_CONFIG[last][1], _GRANULARITY_CONFIG[last][2]


def _resolve_instrument_ids(db: Session, provider_symbols: list[str]) -> dict[str, int]:
    """Map provider_symbol → instrument_id."""
    rows = (
        db.query(MarketDataInstrument.provider_symbol, MarketDataInstrument.id)
        .filter(MarketDataInstrument.provider_symbol.in_(provider_symbols))
        .all()
    )
    return {row[0]: row[1] for row in rows}


def _load_candles_range(
    db: Session,
    bar_model,
    instrument_id: int,
    start: datetime,
    end: datetime,
) -> dict[datetime, float]:
    """Load candle close prices as {open_time: close} dict."""
    rows = (
        db.query(bar_model.open_time, bar_model.close)
        .filter(
            and_(
                bar_model.instrument_id == instrument_id,
                bar_model.open_time >= start,
                bar_model.open_time <= end,
            )
        )
        .order_by(bar_model.open_time)
        .all()
    )
    result: dict[datetime, float] = {}
    for row in rows:
        ts = row[0]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        result[ts] = float(row[1])
    return result


def _interpolate_price(candles: dict[datetime, float], target: datetime) -> Optional[float]:
    """Find the closest candle close price at or before target timestamp.

    Returns None when no candle exists at-or-before *target* so the caller
    can fall back to execution price instead of using a future candle.
    """
    if not candles:
        return None
    best_ts = None
    for ts in candles:
        if ts <= target:
            if best_ts is None or ts > best_ts:
                best_ts = ts
    if best_ts is not None:
        return candles[best_ts]
    return None


def _build_performance_value(
    sorted_ts: list[datetime],
    trade_events: list[tuple[datetime, str, str, Decimal, Decimal, Optional[Decimal]]],
    trade_ts_pairs: set[tuple[datetime, str]],
    asset_candles: dict[str, dict[datetime, float]],
    fx_candles: dict[datetime, float],
    asset_to_provider: dict[str, str],
    instrument_map: dict[str, int],
    use_eur: bool,
    reference_currency: str,
    db: Session,
) -> dict:
    """Build a realized + unrealized PnL time-series (performance_value mode).

    Uses weighted-average cost basis, consistent with
    ``wallet_statistics.service.build_wallet_statistics``.
    """

    def _price_ref(a: str, ts: datetime, exec_prices: dict[str, Decimal]) -> Optional[Decimal]:
        """Price of one unit of *a* in the reference currency at *ts*."""
        is_trade = (ts, a) in trade_ts_pairs
        if is_trade and a in exec_prices:
            if use_eur:
                return exec_prices[a]
            cp = _interpolate_price(asset_candles.get(a, {}), ts)
            if cp is not None:
                return Decimal(str(cp))
            fx = _interpolate_price(fx_candles, ts) if fx_candles else None
            rate = Decimal(str(fx)) if fx else Decimal("1.08")
            return exec_prices[a] * rate

        cp = _interpolate_price(asset_candles.get(a, {}), ts)
        if cp is not None:
            if use_eur:
                fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                return Decimal(str(cp)) / (Decimal(str(fx)) if fx and fx > 0 else Decimal("1.08"))
            return Decimal(str(cp))

        if a in exec_prices:
            if use_eur:
                return exec_prices[a]
            fx = _interpolate_price(fx_candles, ts) if fx_candles else None
            rate = Decimal(str(fx)) if fx else Decimal("1.08")
            return exec_prices[a] * rate
        return None

    trade_idx = 0
    positions: dict[str, Decimal] = defaultdict(Decimal)
    cost_basis: dict[str, Decimal] = defaultdict(Decimal)
    exec_prices: dict[str, Decimal] = {}
    realized_pnl = Decimal("0")
    first_trade_seen = False

    points: list[dict] = []

    for ts in sorted_ts:
        while trade_idx < len(trade_events) and trade_events[trade_idx][0] <= ts:
            _, side, t_asset, amount, t_price, net_eur_sell = trade_events[trade_idx]
            exec_prices[t_asset] = t_price

            if use_eur:
                trade_price_ref = t_price
            else:
                cp = _interpolate_price(asset_candles.get(t_asset, {}), ts)
                if cp is not None:
                    trade_price_ref = Decimal(str(cp))
                else:
                    fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                    rate = Decimal(str(fx)) if fx else Decimal("1.08")
                    trade_price_ref = t_price * rate

            if side == "buy":
                cost_basis[t_asset] += amount * trade_price_ref
                positions[t_asset] += amount
            else:
                if positions[t_asset] > 0:
                    avg_cost = cost_basis[t_asset] / positions[t_asset]
                    cost_basis_consumed = amount * avg_cost
                    # Realized P&L uses net received (not gross) — WAC consistency
                    if net_eur_sell is not None and use_eur:
                        realized_pnl += net_eur_sell - cost_basis_consumed
                    elif net_eur_sell is not None and not use_eur:
                        fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                        rate = Decimal(str(fx)) if fx and fx > 0 else Decimal("1.08")
                        net_usd = net_eur_sell * rate
                        realized_pnl += net_usd - cost_basis_consumed
                    else:
                        realized_pnl += amount * (trade_price_ref - avg_cost)
                    cost_basis[t_asset] -= cost_basis_consumed
                positions[t_asset] -= amount
                if positions[t_asset] <= 0:
                    positions[t_asset] = Decimal("0")
                    cost_basis[t_asset] = Decimal("0")

            first_trade_seen = True
            trade_idx += 1

        if not first_trade_seen:
            continue

        unrealized_pnl = Decimal("0")
        for a, pos in positions.items():
            if pos <= 0:
                continue
            price = _price_ref(a, ts, exec_prices)
            if price is not None:
                unrealized_pnl += pos * price - cost_basis[a]

        total_pnl = realized_pnl + unrealized_pnl
        rounded = total_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        points.append({
            "timestamp": ts.isoformat(),
            "wallet_value": float(rounded),
        })

    # ── Live PnL injection ────────────────────────────────────────
    if any(pos > 0 for pos in positions.values()):
        live_unrealized = Decimal("0")
        eurusdt_rate = get_eurusdt_rate(db, strict=False)
        for a, pos in positions.items():
            if pos <= 0:
                continue
            ps = asset_to_provider.get(a)
            if not ps:
                continue
            iid = instrument_map.get(ps)
            if iid is None:
                continue
            quote = (
                db.query(MarketDataLatestQuote)
                .filter(MarketDataLatestQuote.instrument_id == iid)
                .first()
            )
            if quote and quote.last_price:
                price_usdt = Decimal(str(quote.last_price))
                if use_eur:
                    live_price = usdt_to_eur(price_usdt, eurusdt_rate)
                else:
                    live_price = price_usdt
                live_unrealized += pos * live_price - cost_basis[a]

        total_live_pnl = realized_pnl + live_unrealized
        live_rounded = float(total_live_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        live_ts = datetime.now(timezone.utc)
        live_point = {"timestamp": live_ts.isoformat(), "wallet_value": live_rounded}

        if points:
            last_ts = datetime.fromisoformat(points[-1]["timestamp"])
            if (live_ts - last_ts).total_seconds() < 120:
                points[-1] = live_point
            elif len(points) >= MAX_POINTS:
                points[-1] = live_point
            else:
                points.append(live_point)
        else:
            points.append(live_point)

    return {"currency": reference_currency.upper(), "points": points}


def _apply_history_scope_filter(q, portfolio_scope: Optional[str], portfolio_id: Optional[str]):
    """Apply scope-based filtering to an ExchangeOrder query (wallet_history).

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


def build_wallet_history(
    db: Session,
    client_id,
    reference_currency: str = "EUR",
    asset: Optional[str] = None,
    mode: str = "value",
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[str] = None,
) -> dict:
    """Build the wallet time-series for a client.

    *mode* controls the metric:
      - ``"value"``: NAV = Σ position_i × price_i  (default)
      - ``"performance_value"``: realized PnL + unrealized PnL in ref currency

    When *asset* is provided the series is scoped to that single asset;
    otherwise it covers the whole portfolio.

    *portfolio_scope* / *portfolio_id* narrow to a specific portfolio:
      - None / "global" → all orders (backward compatible)
      - "direct"        → non-bundle orders only
      - "bundle"        → bundle orders for portfolio_id only

    Returns {"currency": …, "points": [{"timestamp": …, "wallet_value": …}]}
    """
    use_eur = reference_currency.upper() == "EUR"

    q = db.query(ExchangeOrder).filter(
        ExchangeOrder.client_id == client_id,
        ExchangeOrder.status == "completed",
    )
    if asset:
        q = q.filter(ExchangeOrder.asset == asset.upper())
    q = _apply_history_scope_filter(q, portfolio_scope, portfolio_id)
    orders = q.order_by(ExchangeOrder.created_at.asc()).all()

    if not orders:
        return {"currency": reference_currency.upper(), "points": []}

    traded_assets: set[str] = set()
    for o in orders:
        traded_assets.add(o.asset)

    provider_symbols = []
    asset_to_provider: dict[str, str] = {}
    for ta in traded_assets:
        ps = ASSET_PROVIDER_SYMBOL_MAP.get(ta, f"{ta}USDT")
        provider_symbols.append(ps)
        asset_to_provider[ta] = ps
    if use_eur:
        provider_symbols.append(EURUSDT_SYMBOL)

    instrument_map = _resolve_instrument_ids(db, provider_symbols)

    first_trade_ts = orders[0].created_at
    if first_trade_ts.tzinfo is None:
        first_trade_ts = first_trade_ts.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    span_hours = (now - first_trade_ts).total_seconds() / 3600

    start_idx, bar_model, interval_sec = _select_granularity(span_hours)

    asset_candles: dict[str, dict[datetime, float]] = {}
    fx_candles: dict[datetime, float] = {}

    def _load_all_candles(model):
        candles: dict[str, dict[datetime, float]] = {}
        for asset, ps in asset_to_provider.items():
            iid = instrument_map.get(ps)
            if iid is None:
                candles[asset] = {}
                continue
            candles[asset] = _load_candles_range(db, model, iid, first_trade_ts, now)
        fx: dict[datetime, float] = {}
        if use_eur:
            fx_iid = instrument_map.get(EURUSDT_SYMBOL)
            if fx_iid is not None:
                fx = _load_candles_range(db, model, fx_iid, first_trade_ts, now)
        return candles, fx

    asset_candles, fx_candles = _load_all_candles(bar_model)
    total_loaded = sum(len(c) for c in asset_candles.values())

    if total_loaded == 0:
        for fallback_idx in range(start_idx + 1, len(_GRANULARITY_CONFIG)):
            _, fb_model, fb_interval = _GRANULARITY_CONFIG[fallback_idx]
            asset_candles, fx_candles = _load_all_candles(fb_model)
            total_loaded = sum(len(c) for c in asset_candles.values())
            if total_loaded > 0:
                bar_model = fb_model
                interval_sec = fb_interval
                logger.info(
                    "Granularity fallback: no data for %s, using %s (%d candles found)",
                    _GRANULARITY_CONFIG[start_idx][1].__tablename__,
                    fb_model.__tablename__,
                    total_loaded,
                )
                break

    if total_loaded == 0:
        logger.warning("No instrument found for any granularity")
    if use_eur and not fx_candles:
        fx_iid = instrument_map.get(EURUSDT_SYMBOL)
        if fx_iid is None:
            logger.warning("EURUSDT instrument not found for FX history")

    trade_events: list[tuple[datetime, str, str, Decimal, Decimal, Optional[Decimal]]] = []
    for o in orders:
        ts = o.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        amt = Decimal(str(o.amount_crypto))
        price = Decimal(str(o.price))
        net_eur_sell: Optional[Decimal] = None
        if o.side == "sell":
            if o.amount_to is not None:
                net_eur_sell = Decimal(str(o.amount_to))
            else:
                gross = Decimal(str(o.amount_fiat))
                fee = Decimal(str(o.fee_amount)) if o.fee_amount else Decimal("0")
                net_eur_sell = gross - fee
        trade_events.append((ts, o.side, o.asset, amt, price, net_eur_sell))

    # O(1) lookup for "is this (timestamp, asset) a trade execution?"
    trade_ts_pairs: set[tuple[datetime, str]] = set()
    for te in trade_events:
        trade_ts_pairs.add((te[0], te[2]))

    # ── Build timeline ──────────────────────────────────────────────
    # Only include trade timestamps + candle timestamps that fall on or
    # after the first trade.  Do NOT add `now` — the live point from
    # MarketDataLatestQuote is appended separately so the chart always
    # ends at the same value displayed by the Current Value hero.
    all_timestamps: set[datetime] = set()
    for te in trade_events:
        all_timestamps.add(te[0])

    best_candle_source = max(asset_candles.values(), key=len) if asset_candles else {}
    for ts in best_candle_source:
        if ts >= first_trade_ts:
            all_timestamps.add(ts)

    sorted_ts = sorted(all_timestamps)

    if len(sorted_ts) > MAX_POINTS:
        step = max(1, len(sorted_ts) // MAX_POINTS)
        trade_ts_set = {ts for ts, *_ in trade_events}
        sampled = set()
        for i in range(0, len(sorted_ts), step):
            sampled.add(sorted_ts[i])
        sampled.update(trade_ts_set)
        sampled.add(sorted_ts[-1])
        sorted_ts = sorted(sampled)
        if len(sorted_ts) > MAX_POINTS:
            sorted_ts = sorted_ts[:MAX_POINTS]

    # ── performance_value mode ────────────────────────────────────
    if mode == "performance_value":
        return _build_performance_value(
            sorted_ts, trade_events, trade_ts_pairs,
            asset_candles, fx_candles, asset_to_provider,
            instrument_map, use_eur, reference_currency, db,
        )

    # ── Reconstruct positions & value series (mode=value) ─────────
    trade_idx = 0
    positions: dict[str, Decimal] = defaultdict(Decimal)
    execution_prices: dict[str, Decimal] = {}

    points: list[dict] = []

    for ts in sorted_ts:
        while trade_idx < len(trade_events) and trade_events[trade_idx][0] <= ts:
            _, side, t_asset, amount, t_price, _ = trade_events[trade_idx]
            if side == "buy":
                positions[t_asset] += amount
            else:
                positions[t_asset] -= amount
                if positions[t_asset] < 0:
                    positions[t_asset] = Decimal("0")
            execution_prices[t_asset] = t_price
            trade_idx += 1

        total_pos = sum(p for p in positions.values() if p > 0)
        if total_pos <= 0:
            continue

        wallet_value = Decimal("0")
        for a, pos in positions.items():
            if pos <= 0:
                continue

            is_trade = (ts, a) in trade_ts_pairs

            if is_trade and a in execution_prices:
                if use_eur:
                    wallet_value += pos * execution_prices[a]
                else:
                    cp = _interpolate_price(asset_candles.get(a, {}), ts)
                    if cp is not None:
                        wallet_value += pos * Decimal(str(cp))
                    else:
                        fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                        rate = Decimal(str(fx)) if fx else Decimal("1.08")
                        wallet_value += pos * execution_prices[a] * rate
            else:
                cp = _interpolate_price(asset_candles.get(a, {}), ts)
                if cp is not None:
                    if use_eur:
                        fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                        if fx and fx > 0:
                            eur_price = Decimal(str(cp)) / Decimal(str(fx))
                        else:
                            eur_price = Decimal(str(cp)) / Decimal("1.08")
                        wallet_value += pos * eur_price
                    else:
                        wallet_value += pos * Decimal(str(cp))
                elif a in execution_prices:
                    if use_eur:
                        wallet_value += pos * execution_prices[a]
                    else:
                        fx = _interpolate_price(fx_candles, ts) if fx_candles else None
                        rate = Decimal(str(fx)) if fx else Decimal("1.08")
                        wallet_value += pos * execution_prices[a] * rate

        if wallet_value > 0:
            rounded = wallet_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            points.append({
                "timestamp": ts.isoformat(),
                "wallet_value": float(rounded),
            })

    # ── Live endpoint value (MUST be the last point) ────────────────
    # Computed from MarketDataLatestQuote — the same source as Current
    # Value in the UI — so the chart endpoint matches the hero metric.
    if positions:
        live_value = Decimal("0")
        eurusdt_rate = get_eurusdt_rate(db, strict=False)
        for a, pos in positions.items():
            if pos <= 0:
                continue
            ps = asset_to_provider.get(a)
            if not ps:
                continue
            iid = instrument_map.get(ps)
            if iid is None:
                continue
            quote = (
                db.query(MarketDataLatestQuote)
                .filter(MarketDataLatestQuote.instrument_id == iid)
                .first()
            )
            if quote and quote.last_price:
                price_usdt = Decimal(str(quote.last_price))
                if use_eur:
                    live_price = usdt_to_eur(price_usdt, eurusdt_rate)
                else:
                    live_price = price_usdt
                live_value += pos * live_price

        if live_value > 0:
            live_rounded = float(live_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            live_ts = datetime.now(timezone.utc)
            live_point = {"timestamp": live_ts.isoformat(), "wallet_value": live_rounded}

            if points:
                last_ts = datetime.fromisoformat(points[-1]["timestamp"])
                if (live_ts - last_ts).total_seconds() < 120:
                    points[-1] = live_point
                elif len(points) >= MAX_POINTS:
                    points[-1] = live_point
                else:
                    points.append(live_point)
            else:
                points.append(live_point)

    return {
        "currency": reference_currency.upper(),
        "points": points,
    }
