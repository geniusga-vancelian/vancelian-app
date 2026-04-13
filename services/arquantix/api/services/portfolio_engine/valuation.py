"""Centralized portfolio valuation functions.

Every page/endpoint must use these helpers so that balances, breakdowns
and charts are computed from a single source of truth.

Pricing chain (invariant):
  MarketDataLatestQuote.last_price (USDT)
  → usdt_to_eur(price, eurusdt_rate)
  → EUR value

FX source:
  get_fx_rate(db) → MarketDataLatestQuote WHERE provider_symbol = 'EURUSDT'
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from database import MarketDataInstrument, MarketDataLatestQuote

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_ROUND = Decimal("0.01")
_INVARIANT_TOLERANCE = Decimal("1.00")


def _dec(v) -> Decimal:
    if v is None:
        return _ZERO
    return Decimal(str(v))


def _f(d: Decimal) -> float:
    return float(d.quantize(_ROUND, rounding=ROUND_HALF_UP))


# ── FX ─────────────────────────────────────────────────────────────

def get_fx_rate(db: Session) -> Decimal:
    """EURUSDT rate from MarketDataLatestQuote (single source).

    Logs the rate, source and timestamp for auditability.
    """
    rate = get_eurusdt_rate(db, strict=False)
    quote = (
        db.query(MarketDataLatestQuote)
        .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
        .filter(MarketDataInstrument.provider_symbol == "EURUSDT")
        .first()
    )
    ts = quote.quote_time.isoformat() if quote and hasattr(quote, "quote_time") and quote.quote_time else "unknown"
    logger.info("FX EURUSDT rate=%.6f timestamp=%s source=MarketDataLatestQuote", float(rate), ts)
    return rate


# ── Single-asset pricing ───────────────────────────────────────────

def get_asset_price_eur(db: Session, asset: str, *, eurusdt_rate: Optional[Decimal] = None) -> Optional[Decimal]:
    """Current price of 1 unit of *asset* in EUR via MarketDataLatestQuote."""
    if eurusdt_rate is None:
        eurusdt_rate = get_eurusdt_rate(db, strict=False)
    ps = ASSET_PROVIDER_SYMBOL_MAP.get(asset, f"{asset}USDT")
    inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.provider_symbol == ps).first()
    if inst is None:
        return None
    quote = db.query(MarketDataLatestQuote).filter(MarketDataLatestQuote.instrument_id == inst.id).first()
    if quote is None or quote.last_price is None:
        return None
    return usdt_to_eur(Decimal(str(quote.last_price)), eurusdt_rate)


def get_asset_value_eur(db: Session, asset: str, quantity: Decimal, *, eurusdt_rate: Optional[Decimal] = None) -> Decimal:
    """Mark-to-market value of *quantity* units of *asset* in EUR."""
    price = get_asset_price_eur(db, asset, eurusdt_rate=eurusdt_rate)
    if price is None:
        return _ZERO
    return (quantity * price).quantize(_ROUND, rounding=ROUND_HALF_UP)


# ── Fiat balance ───────────────────────────────────────────────────

def get_fiat_balance_eur(db: Session, client_id: UUID) -> Decimal:
    """EUR available balance from custody (single source of truth)."""
    from services.accounting.invariants import _get_client_eur_balance
    return _get_client_eur_balance(db, client_id)


# ── Crypto value ───────────────────────────────────────────────────

def get_crypto_value_eur(db: Session, client_id: UUID) -> Decimal:
    """Total crypto NAV in EUR from crypto_positions (consolidated)."""
    from services.accounting.invariants import _get_crypto_value_eur
    return _get_crypto_value_eur(db, client_id)


# ── Portfolio breakdown ────────────────────────────────────────────

def _compute_atoms_value(db: Session, portfolio_id, eurusdt_rate: Decimal) -> Decimal:
    """Sum mark-to-market of open SPOT PositionAtoms for a portfolio.

    Lending/borrowing positions are excluded — they are financial claims,
    not spot holdings, and must not inflate/deflate the crypto NAV.
    """
    from services.portfolio_engine.positions.models import PositionAtom
    from services.portfolio_engine.instruments.price_bridge import get_instrument_price

    _NON_SPOT_TYPES = {"lending", "borrowing", "staking", "collateral"}

    val = _ZERO
    for atom in db.query(PositionAtom).filter(
        PositionAtom.portfolio_id == portfolio_id,
        PositionAtom.status == "open",
        PositionAtom.quantity > 0,
        ~PositionAtom.position_type.in_(_NON_SPOT_TYPES),
    ).all():
        try:
            pi = get_instrument_price(db, atom.instrument_id)
            p_usdt = Decimal(pi["price"]) if pi.get("price") else None
            if p_usdt is not None:
                val += _dec(atom.quantity) * usdt_to_eur(p_usdt, eurusdt_rate)
        except Exception:
            pass
    return val


def get_portfolio_breakdown(db: Session, client_id: UUID) -> dict:
    """Breakdown: fiat + direct crypto + bundles, all in EUR.

    Enforces invariant: direct + bundles ≈ crypto_total (tolerance 1€).
    Logs all values for auditability.
    """
    from services.portfolio_engine.portfolios.models import Portfolio

    eurusdt_rate = get_fx_rate(db)
    fiat = get_fiat_balance_eur(db, client_id)
    crypto_total = get_crypto_value_eur(db, client_id)

    direct_portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.client_id == client_id, Portfolio.portfolio_type == "direct_portfolio", Portfolio.status == "active")
        .first()
    )
    direct_val = _compute_atoms_value(db, direct_portfolio.id, eurusdt_rate) if direct_portfolio else _ZERO

    bundle_portfolios = (
        db.query(Portfolio)
        .filter(Portfolio.client_id == client_id, Portfolio.portfolio_type == "bundle_portfolio", Portfolio.status == "active")
        .all()
    )
    bundle_val = _ZERO
    for bp in bundle_portfolios:
        bundle_val += _compute_atoms_value(db, bp.id, eurusdt_rate)

    # Invariant check: direct + bundles should ≈ crypto_total
    atoms_sum = direct_val + bundle_val
    delta = abs(atoms_sum - crypto_total)
    if delta > _INVARIANT_TOLERANCE:
        logger.error(
            "INVARIANT VIOLATION: direct(%.2f) + bundles(%.2f) = %.2f != crypto_total(%.2f), delta=%.2f",
            float(direct_val), float(bundle_val), float(atoms_sum), float(crypto_total), float(delta),
        )

    total = fiat + crypto_total
    tv = _f(total)

    result = {
        "fiat": _f(fiat),
        "crypto_direct": _f(direct_val),
        "bundles": _f(bundle_val),
        "crypto_total": _f(crypto_total),
        "total_value": tv,
        "fiat_pct": round(float(fiat) / tv * 100, 2) if tv > 0 else 0.0,
        "crypto_direct_pct": round(float(direct_val) / tv * 100, 2) if tv > 0 else 0.0,
        "bundles_pct": round(float(bundle_val) / tv * 100, 2) if tv > 0 else 0.0,
    }

    logger.info(
        "Breakdown: fiat=%.2f crypto_direct=%.2f bundles=%.2f crypto_total=%.2f total=%.2f",
        result["fiat"], result["crypto_direct"], result["bundles"], result["crypto_total"], tv,
    )
    return result


# ── Net external cash flows ───────────────────────────────────────

def get_net_deposits(db: Session, client_id: UUID) -> Decimal:
    """Cumulative external deposits minus withdrawals (EUR)."""
    from services.accounting.invariants import _get_net_external_cash_flows
    return _get_net_external_cash_flows(db, client_id)


# ── Realized / Unrealized P&L ─────────────────────────────────────

def get_pnl(db: Session, client_id: UUID) -> dict:
    """Aggregated realized + unrealized P&L in EUR."""
    from services.accounting.invariants import _get_realized_unrealized
    realized, unrealized = _get_realized_unrealized(db, client_id)
    total = realized + unrealized

    return {
        "realized_pnl": _f(realized),
        "unrealized_pnl": _f(unrealized),
        "total_pnl": _f(total),
    }


# ── Global history builder ────────────────────────────────────────

def build_global_history(db: Session, client_id: UUID, *, period: str = "ALL") -> dict:
    """Build the global equity curve reusing the crypto history timeline.

    The crypto performance_value series from build_wallet_history is
    market-driven (candle-dense), continuous, and already correct.
    This function reuses that series directly — no timeline rebuild,
    no event iteration, no sparse arrays.

    performance_value = crypto PnL (cost-basis WAC)
        Fiat has zero performance (no market risk).
    total_value = crypto NAV + fiat balance (informational only)

    Last point is anchored to live get_pnl() so chart == statistics.

    Returns {period, points: [{timestamp, total_value, performance_value}], max_drawdown}
    """
    from datetime import timedelta
    from decimal import Decimal as D

    from services.wallet_history.service import build_wallet_history
    from services.custody.models import CustodyAccount, CustodyTransaction
    from services.custody.enums import TransactionDirection

    ref_currency = "EUR"

    # ── Single canonical series: performance_value ────────────────
    # This is the SAME call the crypto stats page makes.
    # Its timeline is market-driven (trade ts + candle ts), dense,
    # and continuous — no event gaps.
    crypto_perf_result = build_wallet_history(
        db, client_id, reference_currency=ref_currency,
        mode="performance_value",
    )
    perf_points = crypto_perf_result.get("points", [])

    # NAV series for total_value (same engine, same timestamps)
    crypto_nav_result = build_wallet_history(
        db, client_id, reference_currency=ref_currency,
        mode="value",
    )
    nav_by_ts: dict[str, float] = {
        p["timestamp"]: p.get("wallet_value", 0)
        for p in crypto_nav_result.get("points", [])
    }

    # ── Fiat balance timeline ─────────────────────────────────────
    acc = (
        db.query(CustodyAccount)
        .filter(CustodyAccount.client_id == client_id, CustodyAccount.currency == "EUR")
        .first()
    )
    fiat_events: list[tuple[datetime, float]] = []
    if acc:
        all_txns = (
            db.query(CustodyTransaction)
            .filter(CustodyTransaction.account_id == acc.id, CustodyTransaction.status == "completed")
            .order_by(CustodyTransaction.created_at.asc())
            .all()
        )
        running = D("0")
        for tx in all_txns:
            amt = D(str(tx.amount or 0))
            if tx.direction == TransactionDirection.CREDIT.value:
                running += amt
            else:
                running -= amt
            fiat_events.append((tx.created_at, float(running)))

    current_fiat = float(get_fiat_balance_eur(db, client_id))

    def _fiat_at(ts: datetime) -> float:
        if not fiat_events:
            return current_fiat
        last_known: float | None = None
        for evt_ts, evt_val in fiat_events:
            if evt_ts <= ts:
                last_known = evt_val
            else:
                break
        return last_known if last_known is not None else 0.0

    # ── Build output from perf series (canonical timeline) ────────
    # perf_points drives the timeline — every point in the crypto
    # chart gets a corresponding global point. No merge, no gaps.
    last_nav = 0.0
    points: list[dict] = []
    for pp in perf_points:
        ts_str = pp["timestamp"]
        perf_val = round(pp.get("wallet_value", 0), 2)
        ts = datetime.fromisoformat(ts_str)

        nav_val = nav_by_ts.get(ts_str)
        if nav_val is not None:
            last_nav = nav_val
        crypto_nav_val = last_nav

        fiat_val = _fiat_at(ts)
        total_val = round(crypto_nav_val + fiat_val, 2)
        points.append({
            "timestamp": ts_str,
            "total_value": total_val,
            "performance_value": perf_val,
        })

    # ── Anchor last point to live values ──────────────────────────
    breakdown = get_portfolio_breakdown(db, client_id)
    live_total = breakdown["total_value"]
    pnl = get_pnl(db, client_id)
    live_perf = pnl["total_pnl"]
    now_ts = datetime.now(timezone.utc).isoformat()

    logger.info(
        "GlobalHistory live anchor: total=%.2f perf=%.2f (from get_pnl)",
        live_total, live_perf,
    )

    if points:
        last_ts = datetime.fromisoformat(points[-1]["timestamp"])
        now = datetime.now(timezone.utc)
        if (now - last_ts).total_seconds() < 120:
            points[-1] = {"timestamp": now_ts, "total_value": live_total, "performance_value": live_perf}
        else:
            points.append({"timestamp": now_ts, "total_value": live_total, "performance_value": live_perf})
    else:
        points.append({"timestamp": now_ts, "total_value": live_total, "performance_value": live_perf})

    # ── Period filtering ──────────────────────────────────────────
    if period != "ALL" and points:
        now = datetime.now(timezone.utc)
        delta_map = {
            "1D": timedelta(days=1), "1W": timedelta(weeks=1),
            "1M": timedelta(days=30), "1Y": timedelta(days=365),
        }
        cutoff = now - delta_map.get(period, timedelta(days=36500))
        points = [p for p in points if datetime.fromisoformat(p["timestamp"]) >= cutoff]

    # ── Max drawdown (on performance series) ──────────────────────
    max_drawdown = None
    if len(points) >= 2:
        perf_series = [p["performance_value"] for p in points]
        peak = perf_series[0]
        worst_dd = 0.0
        for v in perf_series:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > worst_dd:
                    worst_dd = dd
        max_drawdown = round(worst_dd, 4) if worst_dd > 0 else None

    logger.info(
        "GlobalHistory: period=%s points=%d last_total=%.2f last_perf=%.2f max_dd=%s",
        period, len(points),
        points[-1]["total_value"] if points else 0,
        points[-1]["performance_value"] if points else 0,
        max_drawdown,
    )

    return {"period": period, "points": points, "max_drawdown": max_drawdown}
