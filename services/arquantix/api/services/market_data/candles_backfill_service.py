"""
Incremental candle backfill: fetch only missing candlesticks from latest DB candle to now.
Supports timeframes 5m, 1h, 4h, 1d, 1w. Additive; does not replace existing ingestion scripts.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from database import MarketDataInstrument
from database import (
    MarketDataBar1m,
    MarketDataBar5m,
    MarketDataBar1h,
    MarketDataBar4h,
    MarketDataBar1d,
    MarketDataBar1w,
)
from services.market_data.binance_client import (
    fetch_klines_1m,
    fetch_klines_5m,
    fetch_klines_1h,
    fetch_klines_4h,
    fetch_klines_1d,
    fetch_klines_1w,
)
from services.market_data.bars_1m_repo import upsert_bar_1m
from services.market_data.bars_5m_repo import upsert_bar_5m
from services.market_data.bars_1h_repo import upsert_bar_1h
from services.market_data.bars_4h_repo import upsert_bar_4h
from services.market_data.bars_1d_repo import upsert_bar_1d
from services.market_data.bars_1w_repo import upsert_bar_1w

logger = logging.getLogger(__name__)

PROVIDER = "binance"

# Timeframe -> (model, fetch_fn, upsert_fn, step_delta, default_fallback_days)
TIMEFRAME_CONFIG: Dict[str, Dict[str, Any]] = {
    "1m": {
        "model": MarketDataBar1m,
        "fetch_fn": fetch_klines_1m,
        "upsert_fn": upsert_bar_1m,
        "step": timedelta(minutes=1),
        "fallback_days": 7,
    },
    "5m": {
        "model": MarketDataBar5m,
        "fetch_fn": fetch_klines_5m,
        "upsert_fn": upsert_bar_5m,
        "step": timedelta(minutes=5),
        "fallback_days": 7,
    },
    "1h": {
        "model": MarketDataBar1h,
        "fetch_fn": fetch_klines_1h,
        "upsert_fn": upsert_bar_1h,
        "step": timedelta(hours=1),
        "fallback_days": 30,
    },
    "4h": {
        "model": MarketDataBar4h,
        "fetch_fn": fetch_klines_4h,
        "upsert_fn": upsert_bar_4h,
        "step": timedelta(hours=4),
        "fallback_days": 120,
    },
    "1d": {
        "model": MarketDataBar1d,
        "fetch_fn": fetch_klines_1d,
        "upsert_fn": upsert_bar_1d,
        "step": timedelta(days=1),
        "fallback_days": 730,
    },
    "1w": {
        "model": MarketDataBar1w,
        "fetch_fn": fetch_klines_1w,
        "upsert_fn": upsert_bar_1w,
        "step": timedelta(weeks=1),
        "fallback_days": 3650,
    },
}

SUPPORTED_TIMEFRAMES = list(TIMEFRAME_CONFIG.keys())
DEFAULT_LIMIT_PER_REQUEST = 500
DEFAULT_COMMIT_BATCH = 5


def load_binance_instruments(
    session: Session,
    symbol: Optional[str] = None,
) -> List[Tuple[int, str]]:
    """
    Load (instrument_id, provider_symbol) for active Binance instruments.
    If symbol is provided, return only that instrument or empty if not found.
    """
    query = (
        session.query(MarketDataInstrument.id, MarketDataInstrument.provider_symbol)
        .filter(
            MarketDataInstrument.provider == PROVIDER,
            MarketDataInstrument.is_active == "true",
        )
        .order_by(MarketDataInstrument.symbol)
    )
    if symbol is not None:
        sym_upper = symbol.strip().upper()
        query = query.filter(MarketDataInstrument.provider_symbol == sym_upper)
    rows = query.all()
    out = []
    for inst_id, provider_symbol in rows:
        sym = (provider_symbol or "").strip()
        if sym:
            out.append((inst_id, sym))
        else:
            logger.warning("Instrument id=%s has empty provider_symbol, skipping", inst_id)
    return out


def get_latest_open_time(
    session: Session,
    timeframe: str,
    instrument_id: int,
) -> Optional[datetime]:
    """Return max(open_time) for the given instrument in the timeframe table, or None if no rows."""
    if timeframe not in TIMEFRAME_CONFIG:
        return None
    model = TIMEFRAME_CONFIG[timeframe]["model"]
    value = (
        session.query(func.max(model.open_time))
        .filter(model.instrument_id == instrument_id)
        .scalar()
    )
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def _dt_to_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def run_backfill(
    session: Session,
    timeframe: str,
    symbol: Optional[str] = None,
    limit_per_request: int = DEFAULT_LIMIT_PER_REQUEST,
    fallback_days: Optional[int] = None,
    commit_batch: int = DEFAULT_COMMIT_BATCH,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run incremental backfill for the given timeframe.
    Fetches missing candles from (latest DB candle + 1 step) or (now - fallback_days) up to now.

    Returns a summary dict: instruments_processed, candles_fetched, candles_upserted,
    commits_performed, errors (list), skipped (list).
    """
    if timeframe not in TIMEFRAME_CONFIG:
        return {
            "instruments_processed": 0,
            "candles_fetched": 0,
            "candles_upserted": 0,
            "commits_performed": 0,
            "errors": [f"Unsupported timeframe: {timeframe}"],
            "skipped": [],
        }

    config = TIMEFRAME_CONFIG[timeframe]
    fetch_fn = config["fetch_fn"]
    upsert_fn = config["upsert_fn"]
    step = config["step"]
    days = fallback_days if fallback_days is not None else config["fallback_days"]

    instruments = load_binance_instruments(session, symbol=symbol)
    if not instruments:
        if symbol:
            return {
                "instruments_processed": 0,
                "candles_fetched": 0,
                "candles_upserted": 0,
                "commits_performed": 0,
                "errors": [f"Symbol not found or inactive: {symbol}"],
                "skipped": [],
            }
        logger.info("No Binance instruments found")
        return {
            "instruments_processed": 0,
            "candles_fetched": 0,
            "candles_upserted": 0,
            "commits_performed": 0,
            "errors": [],
            "skipped": [],
        }

    now_utc = datetime.now(timezone.utc)
    end_ms = _dt_to_ms(now_utc)
    total_fetched = 0
    total_upserted = 0
    commits_performed = 0
    errors: List[str] = []
    skipped: List[str] = []
    batch_count_since_commit = 0
    instrument_details: List[Dict[str, Any]] = []

    logger.info(
        "Backfill %s: timeframe=%s symbols=%s limit_per_request=%s fallback_days=%s commit_batch=%s dry_run=%s",
        "DRY-RUN" if dry_run else "START",
        timeframe,
        [s for _, s in instruments],
        limit_per_request,
        days,
        commit_batch,
        dry_run,
    )

    for instrument_id, provider_symbol in instruments:
        instrument_fetched = 0
        instrument_upserted = 0
        try:
            latest = get_latest_open_time(session, timeframe, instrument_id)
            if latest is not None:
                start_dt = latest + step
                logger.info(
                    "%s: latest DB candle open_time=%s, backfill from %s",
                    provider_symbol,
                    latest.isoformat(),
                    start_dt.isoformat(),
                )
            else:
                start_dt = now_utc - timedelta(days=days)
                logger.info(
                    "%s: no existing candle, using fallback start %s (last %s days)",
                    provider_symbol,
                    start_dt.isoformat(),
                    days,
                )

            start_ms = _dt_to_ms(start_dt)
            if start_ms >= end_ms:
                logger.info("%s: already up to date, skip", provider_symbol)
                instrument_details.append({
                    "instrument_id": instrument_id,
                    "provider_symbol": provider_symbol,
                    "candles_fetched": 0,
                    "candles_upserted": 0,
                })
                continue

            last_open_time_after_batch: Optional[datetime] = None

            while True:
                batch = fetch_fn(
                    provider_symbol,
                    limit=limit_per_request,
                    start_time_ms=start_ms,
                    end_time_ms=end_ms,
                )
                if batch is None:
                    errors.append(
                        f"{provider_symbol} ({timeframe}): appel Binance échoué (start={start_ms}, end={end_ms})"
                    )
                    logger.warning("%s: fetch_fn returned None", provider_symbol)
                    instrument_details.append({
                        "instrument_id": instrument_id,
                        "provider_symbol": provider_symbol,
                        "candles_fetched": instrument_fetched,
                        "candles_upserted": instrument_upserted,
                        "error": "fetch failed",
                    })
                    break
                if not batch:
                    logger.debug("%s: no more candles from Binance", provider_symbol)
                    break

                batch_last_open: Optional[datetime] = None
                batch_upserted = 0
                for c in batch:
                    ot = c.get("open_time")
                    if ot is None:
                        continue
                    if isinstance(ot, datetime) and ot.tzinfo is None:
                        ot = ot.replace(tzinfo=timezone.utc)
                    batch_last_open = ot
                    instrument_fetched += 1
                    if not dry_run:
                        upsert_fn(
                            session,
                            instrument_id=instrument_id,
                            open_time=ot,
                            open=c["open"],
                            high=c["high"],
                            low=c["low"],
                            close=c["close"],
                            volume=c["volume"],
                            source=PROVIDER,
                        )
                        instrument_upserted += 1
                        batch_upserted += 1

                total_fetched += len(batch)
                total_upserted += batch_upserted

                if batch_last_open is None:
                    break
                if last_open_time_after_batch is not None and batch_last_open <= last_open_time_after_batch:
                    logger.warning(
                        "%s: batch did not advance cursor (last=%s), stop to avoid loop",
                        provider_symbol,
                        batch_last_open.isoformat(),
                    )
                    break
                last_open_time_after_batch = batch_last_open
                next_start_dt = batch_last_open + step
                batch_count_since_commit += 1  # compté dès qu’un lot est traité (y compris le dernier)

                if not dry_run and commit_batch > 0 and batch_count_since_commit >= commit_batch:
                    try:
                        session.commit()
                        commits_performed += 1
                        batch_count_since_commit = 0
                        logger.info(
                            "%s: committed after batch (total upserted so far %s)",
                            provider_symbol,
                            total_upserted,
                        )
                    except Exception as e:
                        session.rollback()
                        errors.append(f"{provider_symbol}: commit failed: {e!s}")
                        logger.exception("Commit failed for %s", provider_symbol)
                        break
                if next_start_dt >= now_utc:
                    break
                start_ms = _dt_to_ms(next_start_dt)

            if instrument_fetched > 0:
                logger.info(
                    "%s: fetched=%s upserted=%s",
                    provider_symbol,
                    instrument_fetched,
                    instrument_upserted if not dry_run else "(dry-run)",
                )
            instrument_details.append({
                "instrument_id": instrument_id,
                "provider_symbol": provider_symbol,
                "candles_fetched": instrument_fetched,
                "candles_upserted": instrument_upserted,
            })

        except Exception as e:
            msg = f"{provider_symbol}: {e!s}"
            errors.append(msg)
            logger.exception("Backfill failed for %s", provider_symbol)
            instrument_details.append({
                "instrument_id": instrument_id,
                "provider_symbol": provider_symbol,
                "candles_fetched": instrument_fetched,
                "candles_upserted": instrument_upserted,
                "error": msg,
            })
            if not dry_run:
                try:
                    session.rollback()
                except Exception:
                    pass

    if not dry_run and batch_count_since_commit > 0:
        try:
            session.commit()
            commits_performed += 1
            logger.info("Final commit (remaining batch)")
        except Exception as e:
            session.rollback()
            errors.append(f"Final commit failed: {e!s}")
            logger.exception("Final commit failed")

    summary = {
        "instruments_processed": len(instruments),
        "candles_fetched": total_fetched,
        "candles_upserted": total_upserted,
        "commits_performed": commits_performed,
        "errors": errors,
        "skipped": skipped,
        "instrument_details": instrument_details,
    }
    logger.info(
        "Backfill %s complete: instruments=%s fetched=%s upserted=%s commits=%s errors=%s",
        "DRY-RUN " if dry_run else "",
        summary["instruments_processed"],
        summary["candles_fetched"],
        summary["candles_upserted"],
        summary["commits_performed"],
        len(summary["errors"]),
    )
    return summary
