"""
Top movers: rankings (top gainers, losers, volume) from market summary data.
Uses market_summary_repo; read-only, no commit.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.quotes_repo import get_latest_quotes_by_instrument_ids
from services.market_data.market_summary_repo import get_market_summaries

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def _eligible_binance_instrument_ids(session: Session) -> List[int]:
    """Return instrument IDs that are Binance, active, and have a latest quote."""
    rows = (
        session.query(MarketDataInstrument.id)
        .filter(
            MarketDataInstrument.provider == "binance",
            MarketDataInstrument.is_active == "true",
        )
        .all()
    )
    ids = [r[0] for r in rows]
    if not ids:
        return []
    quotes = get_latest_quotes_by_instrument_ids(session, ids)
    return [q.instrument_id for q in quotes]


def get_top_movers(
    session: Session,
    limit: int = DEFAULT_LIMIT,
    provider_symbols: Optional[List[str]] = None,
) -> dict:
    """
    Return top_gainers, top_losers, top_volume (each a list of summary dicts).
    Uses get_market_summaries; then sorts and slices. limit applied to each list (max MAX_LIMIT).
    """
    limit = max(1, min(limit, MAX_LIMIT))
    if provider_symbols:
        sym_list = [s.strip().upper() for s in provider_symbols if s and s.strip()]
        summaries = get_market_summaries(session, provider_symbols=sym_list) if sym_list else []
    else:
        eligible_ids = _eligible_binance_instrument_ids(session)
        summaries = get_market_summaries(session, instrument_ids=eligible_ids) if eligible_ids else []

    with_pct = [s for s in summaries if s.get("change_24h_pct") is not None]
    top_gainers = sorted(with_pct, key=lambda s: s["change_24h_pct"], reverse=True)[:limit]
    top_losers = sorted(with_pct, key=lambda s: s["change_24h_pct"])[:limit]
    top_volume = sorted(summaries, key=lambda s: s["volume_24h"], reverse=True)[:limit]

    return {
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "top_volume": top_volume,
    }
