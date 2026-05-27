"""
Market summary: derived data from latest quotes + 5m candles (24h window).
When live_fallback_binance_sec is set, may fetch from Binance REST and commit
for instruments with provider=binance if the quote is missing or stale.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.quotes_repo import get_latest_quotes_by_instrument_ids, upsert_latest_quote
from services.market_data.bars_5m_repo import get_bars_5m

logger = logging.getLogger(__name__)

# 24h window for change and sparkline
WINDOW_24H_HOURS = 24
# 5m bars in 24h: 24 * 60 / 5 = 288
MAX_5M_BARS_24H = 300
# Default: consider quote stale after this many seconds (Binance REST fallback)
LIVE_FALLBACK_STALE_SEC = 60


def _resolve_instruments(
    session: Session,
    instrument_ids: Optional[List[int]] = None,
    provider_symbols: Optional[List[str]] = None,
) -> List[Tuple[int, str, str]]:
    """Return unique (instrument_id, provider_symbol, provider) for requested ids and/or symbols."""
    result: Dict[int, Tuple[str, str]] = {}
    if instrument_ids:
        rows = (
            session.query(
                MarketDataInstrument.id,
                MarketDataInstrument.provider_symbol,
                MarketDataInstrument.provider,
            )
            .filter(MarketDataInstrument.id.in_(instrument_ids))
            .all()
        )
        for iid, ps, prov in rows:
            result[iid] = ((ps or "").strip(), (prov or "").strip().lower())
    if provider_symbols:
        sym_list = [s.strip().upper() for s in provider_symbols if s and s.strip()]
        if sym_list:
            rows = (
                session.query(
                    MarketDataInstrument.id,
                    MarketDataInstrument.provider_symbol,
                    MarketDataInstrument.provider,
                )
                .filter(MarketDataInstrument.provider_symbol.in_(sym_list))
                .all()
            )
            for iid, ps, prov in rows:
                result[iid] = ((ps or "").strip(), (prov or "").strip().lower())
    return [(iid, result[iid][0], result[iid][1]) for iid in sorted(result.keys())]


def refresh_binance_quotes_for_provider_symbols(
    session: Session,
    provider_symbols: List[str],
    max_age_sec: Optional[int] = 30,
) -> None:
    """
    Pour une liste de symboles (ex. BTCUSDT, ETHUSDT), met à jour les quotes en base
    en appelant Binance REST pour ceux qui sont des instruments Binance.
    Si max_age_sec est donné, ne rafraîchit que si la quote est absente ou plus vieille que max_age_sec.
    """
    if not provider_symbols:
        return
    instruments = _resolve_instruments(session, provider_symbols=[s.strip().upper() for s in provider_symbols if s])
    ids = [iid for iid, _, _ in instruments]
    if not ids:
        return
    quotes = get_latest_quotes_by_instrument_ids(session, ids)
    quote_by_id = {q.instrument_id: q for q in quotes}
    now_utc = datetime.now(timezone.utc)
    for instrument_id, provider_symbol, provider in instruments:
        if provider != "binance" or not provider_symbol:
            continue
        if max_age_sec is not None:
            q = quote_by_id.get(instrument_id)
            if q and q.updated_at:
                utc_updated = q.updated_at if q.updated_at.tzinfo else q.updated_at.replace(tzinfo=timezone.utc)
                if (now_utc - utc_updated).total_seconds() < max_age_sec:
                    continue
        _fetch_binance_and_upsert(session, instrument_id, provider_symbol)


def _quote_is_stale(quote, now_utc: datetime, max_age_sec: int) -> bool:
    """True if quote is missing or older than max_age_sec."""
    if quote is None:
        return True
    if not quote.updated_at:
        return True
    utc_updated = quote.updated_at if quote.updated_at.tzinfo else quote.updated_at.replace(tzinfo=timezone.utc)
    return (now_utc - utc_updated).total_seconds() >= max_age_sec


def _price_from_quote(quote) -> Optional[float]:
    if quote is None:
        return None
    try:
        return float(quote.last_price)
    except (TypeError, ValueError):
        return 0.0


def _fetch_binance_and_upsert(
    session: Session,
    instrument_id: int,
    provider_symbol: str,
) -> Optional[float]:
    """
    Fetch latest price from Binance REST, upsert into market_data_latest_quotes, commit.
    Returns last_price or None on failure.
    """
    try:
        from services.market_data.binance_client import fetch_ticker
        quote = fetch_ticker(provider_symbol)
        if not quote:
            return None
        upsert_latest_quote(
            session,
            instrument_id=instrument_id,
            provider="binance",
            provider_symbol=quote.get("provider_symbol") or provider_symbol,
            last_price=quote["last_price"],
            bid_price=quote.get("bid_price"),
            ask_price=quote.get("ask_price"),
            volume=quote.get("volume"),
            quote_time=quote.get("quote_time"),
        )
        session.commit()
        return float(quote["last_price"])
    except Exception as e:
        logger.warning("Binance live fallback failed for %s: %s", provider_symbol, e)
        try:
            session.rollback()
        except Exception:
            pass
        return None


def get_market_summaries(
    session: Session,
    instrument_ids: Optional[List[int]] = None,
    provider_symbols: Optional[List[str]] = None,
    live_fallback_binance_sec: Optional[int] = LIVE_FALLBACK_STALE_SEC,
    include_eur: bool = False,
) -> List[dict]:
    """
    Compute market summary per instrument: price, 24h change (abs/pct), volume_24h, sparkline_24h.
    Uses latest quote + 5m candles over last 24h. Instruments without a latest quote are skipped.

    When live_fallback_binance_sec is set (default 60), for provider=binance instruments with
    no quote or quote older than that many seconds, fetches from Binance REST and upserts to DB
    so the returned price is up to date even when the WebSocket worker is not running.
    """
    if not instrument_ids and not provider_symbols:
        return []
    instruments = _resolve_instruments(session, instrument_ids=instrument_ids, provider_symbols=provider_symbols)
    if not instruments:
        return []

    ids = [iid for iid, _, _ in instruments]
    id_to_symbol = {iid: sym for iid, sym, _ in instruments}

    quotes = get_latest_quotes_by_instrument_ids(session, ids)
    quote_by_id = {q.instrument_id: q for q in quotes}

    eurusdt_rate = None
    if include_eur:
        from services.market_data.fx import get_eurusdt_rate
        eurusdt_rate = float(get_eurusdt_rate(session, strict=False))

    now_utc = datetime.now(timezone.utc)
    start_24h = now_utc - timedelta(hours=WINDOW_24H_HOURS)

    summaries = []
    for instrument_id, provider_symbol, provider in instruments:
        quote = quote_by_id.get(instrument_id)
        price = _price_from_quote(quote)

        needs_binance_fallback = (
            live_fallback_binance_sec is not None
            and provider == "binance"
            and provider_symbol
            and (price is None or _quote_is_stale(quote, now_utc, live_fallback_binance_sec))
        )
        if needs_binance_fallback:
            live_price = _fetch_binance_and_upsert(session, instrument_id, provider_symbol)
            if live_price is not None:
                price = live_price
            elif price is None:
                price = _price_from_quote(quote_by_id.get(instrument_id))

        if price is None:
            continue

        price_eur = None
        if eurusdt_rate and eurusdt_rate > 0:
            price_eur = price / eurusdt_rate

        bars = get_bars_5m(
            session,
            instrument_id,
            start_time=start_24h,
            end_time=now_utc,
            limit=MAX_5M_BARS_24H,
        )

        if not bars:
            entry = {
                "instrument_id": instrument_id,
                "symbol": provider_symbol,
                "price": price,
                "change_24h_abs": None,
                "change_24h_pct": None,
                "volume_24h": 0.0,
                "sparkline_24h": [],
            }
            if include_eur:
                entry["price_eur"] = price_eur
            summaries.append(entry)
            continue

        reference_price = float(bars[0].close)
        volume_24h = sum(float(b.volume) for b in bars)
        sparkline_24h = [float(b.close) for b in bars]

        if reference_price == 0:
            change_24h_abs = None
            change_24h_pct = None
        else:
            change_24h_abs = price - reference_price
            change_24h_pct = ((price - reference_price) / reference_price) * 100.0

        entry = {
            "instrument_id": instrument_id,
            "symbol": provider_symbol,
            "price": price,
            "change_24h_abs": change_24h_abs,
            "change_24h_pct": change_24h_pct,
            "volume_24h": volume_24h,
            "sparkline_24h": sparkline_24h,
        }
        if include_eur:
            entry["price_eur"] = price_eur
        summaries.append(entry)

    return summaries
