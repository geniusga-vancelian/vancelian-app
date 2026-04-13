"""
Binance 1w candle ingestion: load instruments, fetch 1w klines, upsert into market_data_bars_1w.
Separate from FastAPI lifecycle. Caller opens session; this module commits once per run.
"""
import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.binance_client import fetch_klines_1w
from services.market_data.bars_1w_repo import upsert_bar_1w

logger = logging.getLogger(__name__)

PROVIDER = "binance"
DEFAULT_KLINES_LIMIT = 500


def load_binance_instruments(session: Session) -> List[Tuple[int, str]]:
    """Load (instrument_id, provider_symbol) for provider=binance, is_active=true."""
    rows = (
        session.query(MarketDataInstrument.id, MarketDataInstrument.provider_symbol)
        .filter(
            MarketDataInstrument.provider == PROVIDER,
            MarketDataInstrument.is_active == "true",
        )
        .order_by(MarketDataInstrument.symbol)
        .all()
    )
    out = []
    for inst_id, provider_symbol in rows:
        sym = (provider_symbol or "").strip()
        if sym:
            out.append((inst_id, sym))
        else:
            logger.warning("Instrument id=%s has empty provider_symbol, skipping", inst_id)
    return out


def run_one_cycle(session: Session, limit_per_symbol: int = DEFAULT_KLINES_LIMIT) -> Tuple[int, int, List[str]]:
    """
    Fetch recent 1w klines for each Binance instrument and upsert into market_data_bars_1w.
    Returns (candles_upserted, failure_count, list of error messages).
    """
    instruments = load_binance_instruments(session)
    if not instruments:
        logger.info("No Binance instruments found (provider=binance, is_active=true)")
        return 0, 0, []

    total_upserted = 0
    failures = []
    for instrument_id, provider_symbol in instruments:
        try:
            candles = fetch_klines_1w(provider_symbol, limit=limit_per_symbol)
            if not candles:
                failures.append(f"{provider_symbol}: no klines from Binance")
                continue
            for c in candles:
                upsert_bar_1w(
                    session,
                    instrument_id=instrument_id,
                    open_time=c["open_time"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                    source=PROVIDER,
                )
                total_upserted += 1
        except Exception as e:
            msg = f"{provider_symbol}: {e!s}"
            failures.append(msg)
            logger.exception("1w candle ingestion failed for %s", provider_symbol)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception("Commit failed: %s", e)
        return 0, len(instruments), [f"Commit failed: {e!s}"]

    return total_upserted, len(failures), failures
