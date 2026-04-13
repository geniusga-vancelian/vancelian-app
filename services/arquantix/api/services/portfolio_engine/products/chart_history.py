"""
Weighted performance chart for bundle products.

Given a product with N constituents (e.g. BTC 70%, ETH 30%), this service:
1. Fetches chart-history candles for each constituent asset (same period/timeframe).
2. Aligns all series by timestamp (inner-join: only shared timestamps).
3. Computes a composite index starting at 100:
     composite[t] = sum_i( weight_i * close_i[t] / close_i[t0] ) * 100
   where t0 is the first aligned timestamp.
4. Returns the series in the same format as chart-history for direct use
   by the Flutter performance chart widget.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.chart_period_config import CHART_PERIODS, get_chart_period_rule
from services.market_data.bars_5m_repo import get_bars_5m
from services.market_data.bars_1h_repo import get_bars_1h
from services.market_data.bars_4h_repo import get_bars_4h
from services.market_data.bars_1d_repo import get_bars_1d
from services.market_data.bars_1w_repo import get_bars_1w

from ..templates.models import PortfolioTemplate, TemplateAllocation
from ..instruments.models import Instrument
from ..assets.models import Asset

logger = logging.getLogger(__name__)


def _get_bars(session, timeframe: str, instrument_id: int, start, end, limit: int):
    """Fetch bars for the correct timeframe."""
    fn = {
        "5m": get_bars_5m,
        "1h": get_bars_1h,
        "4h": get_bars_4h,
        "1d": get_bars_1d,
        "1w": get_bars_1w,
    }.get(timeframe)
    if fn is None:
        return []
    return fn(session, instrument_id, start_time=start, end_time=end, limit=limit)


def _resolve_market_data_instrument(
    session: Session, asset_symbol: str
) -> Optional[MarketDataInstrument]:
    """Map a PE asset symbol (e.g. 'BTC') to the market_data_instruments row."""
    provider_symbol = f"{asset_symbol.upper()}USDT"
    inst = (
        session.query(MarketDataInstrument)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    if inst:
        return inst
    return (
        session.query(MarketDataInstrument)
        .filter(MarketDataInstrument.symbol == asset_symbol.upper())
        .first()
    )


def get_product_chart_history(
    session: Session,
    *,
    product_id: UUID,
    period: str,
) -> Optional[Dict[str, Any]]:
    """Compute the weighted composite chart for a bundle product."""
    if period not in CHART_PERIODS:
        return None

    rule = get_chart_period_rule(period)
    if not rule:
        return None

    template = (
        session.query(PortfolioTemplate)
        .filter(PortfolioTemplate.product_id == product_id)
        .first()
    )
    if not template:
        logger.warning("No template found for product %s", product_id)
        return None

    rows = (
        session.query(TemplateAllocation, Instrument, Asset)
        .join(Instrument, TemplateAllocation.instrument_id == Instrument.id)
        .join(Asset, Instrument.asset_id == Asset.id)
        .filter(TemplateAllocation.template_id == template.id)
        .order_by(TemplateAllocation.target_weight.desc())
        .all()
    )
    if not rows:
        logger.warning("No allocations for template %s", template.id)
        return None

    end_time = datetime.now(timezone.utc)
    start_time = end_time - rule.lookback

    # For each constituent: { asset_symbol, weight, bars_by_timestamp }
    constituents: List[Dict[str, Any]] = []
    for ta, instr, asset in rows:
        weight = float(ta.target_weight) if isinstance(ta.target_weight, Decimal) else float(ta.target_weight)
        if weight <= 0:
            continue

        md_inst = _resolve_market_data_instrument(session, asset.symbol)
        if not md_inst:
            logger.warning(
                "No market_data_instruments match for asset %s (%s)", asset.symbol, asset.id
            )
            continue

        bars = _get_bars(
            session,
            rule.timeframe,
            md_inst.id,
            start_time,
            end_time,
            rule.limit,
        )
        if not bars:
            logger.warning(
                "No bars for %s (%s) period=%s", asset.symbol, md_inst.provider_symbol, period
            )
            continue

        bars_map: Dict[str, float] = {}
        for b in bars:
            ts = b.open_time.isoformat() if b.open_time else None
            if ts:
                bars_map[ts] = float(b.close)

        constituents.append({
            "symbol": asset.symbol,
            "provider_symbol": md_inst.provider_symbol or asset.symbol,
            "weight": weight,
            "bars_map": bars_map,
        })

    if not constituents:
        return None

    # Normalize weights to sum to 1.0
    total_weight = sum(c["weight"] for c in constituents)
    if total_weight <= 0:
        return None
    for c in constituents:
        c["weight"] /= total_weight

    # Inner-join: keep only timestamps present in ALL constituents
    common_timestamps = set(constituents[0]["bars_map"].keys())
    for c in constituents[1:]:
        common_timestamps &= set(c["bars_map"].keys())

    if not common_timestamps:
        logger.warning("No common timestamps across constituents for product %s", product_id)
        return None

    sorted_timestamps = sorted(common_timestamps)

    # Initial prices at t0
    t0 = sorted_timestamps[0]
    initial_prices = {}
    for c in constituents:
        p0 = c["bars_map"][t0]
        if p0 <= 0:
            return None
        initial_prices[c["symbol"]] = p0

    # Build composite index series (base = 100)
    points: List[Dict[str, Any]] = []
    for ts in sorted_timestamps:
        composite = 0.0
        for c in constituents:
            price = c["bars_map"][ts]
            p0 = initial_prices[c["symbol"]]
            composite += c["weight"] * (price / p0)
        value = composite * 100.0

        points.append({
            "open_time": ts,
            "value": round(value, 4),
        })

    # Compute overall performance
    if len(points) >= 2:
        perf_pct = round(points[-1]["value"] - points[0]["value"], 4)
    else:
        perf_pct = 0.0

    return {
        "product_id": str(product_id),
        "period": period,
        "timeframe": rule.timeframe,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "base_value": 100,
        "performance_pct": perf_pct,
        "constituents": [
            {
                "symbol": c["symbol"],
                "provider_symbol": c["provider_symbol"],
                "weight": round(c["weight"], 6),
            }
            for c in constituents
        ],
        "points": points,
    }
