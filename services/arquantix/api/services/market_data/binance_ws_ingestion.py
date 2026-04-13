"""
Binance Spot WebSocket ingestion for latest quotes (bookTicker stream).
Runs as a separate process; not part of FastAPI startup.
Uses combined stream, batch commits, reconnect with backoff.
"""
import asyncio
import json
import logging
import signal
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database import MarketDataInstrument, SessionLocal
from services.market_data.config import (
    BINANCE_WS_BASE_URL,
    BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE,
    BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC,
    BINANCE_WS_RECONNECT_BASE_DELAY_SEC,
    BINANCE_WS_RECONNECT_MAX_DELAY_SEC,
)
from services.market_data.quotes_repo import upsert_latest_quote

logger = logging.getLogger(__name__)

PROVIDER = "binance"


def load_binance_instruments(session: Session) -> List[Tuple[int, str]]:
    """Load (instrument_id, provider_symbol) for provider=binance, is_active=true, non-empty provider_symbol."""
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
            out.append((inst_id, sym.upper()))
        else:
            logger.warning("Instrument id=%s has empty provider_symbol, skipping", inst_id)
    return out


def _build_symbol_map_and_streams(
    session: Session,
) -> Tuple[Dict[str, int], List[str]]:
    """Return (symbol_upper -> instrument_id, list of stream names for URL, e.g. btcusdt@bookTicker)."""
    instruments = load_binance_instruments(session)
    symbol_to_id = {provider_symbol: inst_id for inst_id, provider_symbol in instruments}
    stream_names = [f"{provider_symbol.lower()}@bookTicker" for _, provider_symbol in instruments]
    return symbol_to_id, stream_names


def _parse_book_ticker(data: Dict[str, Any], received_at: datetime) -> Optional[Tuple[float, float, float, datetime]]:
    """From bookTicker data dict return (last_price, bid_price, ask_price, quote_time) or None."""
    try:
        b = data.get("b")
        a = data.get("a")
        if b is None or a is None:
            return None
        bid = float(b)
        ask = float(a)
        last = (bid + ask) / 2.0
        # Event time if present (ms)
        e = data.get("E") or data.get("e")
        if e is not None:
            try:
                quote_time = datetime.fromtimestamp(int(e) / 1000.0, tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                quote_time = received_at
        else:
            quote_time = received_at
        return (last, bid, ask, quote_time)
    except (TypeError, ValueError, KeyError):
        return None


def _flush_pending(
    pending: Dict[str, Dict[str, Any]],
    symbol_to_id: Dict[str, int],
) -> int:
    """Sync: open session, upsert each pending quote, commit, return count. Caller clears pending after."""
    if not pending:
        return 0
    db = SessionLocal()
    try:
        for symbol_upper, row in pending.items():
            instrument_id = symbol_to_id.get(symbol_upper)
            if instrument_id is None:
                continue
            upsert_latest_quote(
                db,
                instrument_id=instrument_id,
                provider=PROVIDER,
                provider_symbol=symbol_upper,
                last_price=row["last_price"],
                bid_price=row["bid_price"],
                ask_price=row["ask_price"],
                volume=None,
                quote_time=row["quote_time"],
            )
        db.commit()

        _check_price_alerts(pending)

        return len(pending)
    except Exception as e:
        db.rollback()
        logger.exception("DB flush failed: %s", e)
        return 0
    finally:
        db.close()


def _check_price_alerts(pending: Dict[str, Dict[str, Any]]) -> None:
    """Forward price ticks to the PriceAlertEngine. Fail-safe: never blocks ingestion."""
    try:
        from services.price_alerts.engine import get_alert_engine
        engine = get_alert_engine()
        if engine is None:
            return
        triggered = engine.on_price_batch(pending, SessionLocal)
        if triggered > 0:
            logger.info("PriceAlertEngine triggered %d alert(s) from %d symbol(s)", triggered, len(pending))
    except Exception:
        try:
            from services.price_alerts.metrics import get_metrics
            get_metrics().record_redis_error()
        except Exception:
            pass
        logger.warning("Price alert check failed (engine error)", exc_info=True)


async def run_ws_ingestion_loop(
    symbol_to_id: Dict[str, int],
    stream_names: List[str],
    commit_batch_size: int,
    commit_interval_sec: float,
    reconnect_base_delay: float,
    reconnect_max_delay: float,
    shutdown: asyncio.Event,
) -> None:
    """Long-running async loop: connect to Binance combined stream, parse bookTicker, batch upsert, reconnect on disconnect."""
    import websockets

    base_url = (BINANCE_WS_BASE_URL or "wss://stream.binance.com:9443").rstrip("/")
    streams_param = "/".join(stream_names)
    url = f"{base_url}/stream?streams={streams_param}"

    pending: Dict[str, Dict[str, Any]] = {}
    last_commit_time = time.monotonic()
    delay = reconnect_base_delay
    updates_since_start = 0

    while not shutdown.is_set():
        try:
            logger.info("Connecting to Binance WebSocket: %s", base_url)
            logger.info("Subscribed streams (%d): %s", len(stream_names), ", ".join(stream_names[:5]) + ("..." if len(stream_names) > 5 else ""))
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                delay = reconnect_base_delay
                while not shutdown.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    except asyncio.TimeoutError:
                        continue
                    try:
                        payload = json.loads(msg)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if not isinstance(payload, dict):
                        continue
                    stream_name = payload.get("stream") or ""
                    data = payload.get("data")
                    if not isinstance(data, dict):
                        continue
                    symbol_from_stream = stream_name.replace("@bookTicker", "").upper()
                    instrument_id = symbol_to_id.get(symbol_from_stream)
                    if instrument_id is None:
                        continue
                    received_at = datetime.now(timezone.utc)
                    parsed = _parse_book_ticker(data, received_at)
                    if parsed is None:
                        continue
                    last_price, bid_price, ask_price, quote_time = parsed
                    pending[symbol_from_stream] = {
                        "last_price": last_price,
                        "bid_price": bid_price,
                        "ask_price": ask_price,
                        "quote_time": quote_time,
                    }
                    updates_since_start += 1

                    now = time.monotonic()
                    should_commit = (
                        len(pending) >= commit_batch_size
                        or (now - last_commit_time) >= commit_interval_sec
                    )
                    if should_commit and pending:
                        batch = dict(pending)
                        n = await asyncio.get_event_loop().run_in_executor(
                            None,
                            _flush_pending,
                            batch,
                            symbol_to_id,
                        )
                        if n > 0:
                            logger.debug("Committed %d quote(s)", n)
                        for k in batch:
                            pending.pop(k, None)
                        last_commit_time = now

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("WebSocket error (reconnecting): %s", e)
        if shutdown.is_set():
            break
        logger.info("Reconnecting in %.1fs (backoff)", delay)
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
        delay = min(delay * 2, reconnect_max_delay)

    if pending:
        n = await asyncio.get_event_loop().run_in_executor(
            None,
            _flush_pending,
            pending,
            symbol_to_id,
        )
        if n > 0:
            logger.info("Final commit: %d quote(s)", n)


def _init_price_alert_subsystem() -> None:
    """Bootstrap PriceAlertEngine + NotificationDispatcher inside this worker process."""
    try:
        from services.redis_client import get_redis
        from services.price_alerts.engine import init_alert_engine
        from services.price_alerts.cache import load_all_active_alerts
        from services.notifications.dispatcher import init_dispatcher

        init_dispatcher(SessionLocal)
        r = get_redis()
        engine = init_alert_engine(r)
        if engine is None:
            logger.warning("PriceAlertEngine disabled (Redis unavailable)")
            return
        db = SessionLocal()
        try:
            count = load_all_active_alerts(r, db)
            logger.info("PriceAlertEngine ready — %d active alert(s) loaded", count)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to initialize PriceAlertEngine in WS worker")


def run_ws_ingestion() -> None:
    """
    Load instruments, build stream URL, run async ingestion loop until interrupted.
    Uses one combined WebSocket connection; batch commits; reconnect with backoff.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    db = SessionLocal()
    try:
        symbol_to_id, stream_names = _build_symbol_map_and_streams(db)
    finally:
        db.close()

    if not stream_names:
        logger.warning("No Binance instruments with provider_symbol found. Exiting.")
        return

    logger.info("Loaded %d Binance instrument(s) for bookTicker subscription", len(stream_names))

    _init_price_alert_subsystem()
    shutdown = asyncio.Event()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def on_signal():
        logger.info("Shutdown requested")
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, on_signal)
        except (ValueError, OSError, NotImplementedError):
            pass

    try:
        loop.run_until_complete(
            run_ws_ingestion_loop(
                symbol_to_id=symbol_to_id,
                stream_names=stream_names,
                commit_batch_size=max(1, BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE),
                commit_interval_sec=max(0.5, BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC),
                reconnect_base_delay=max(0.5, BINANCE_WS_RECONNECT_BASE_DELAY_SEC),
                reconnect_max_delay=max(5.0, BINANCE_WS_RECONNECT_MAX_DELAY_SEC),
                shutdown=shutdown,
            )
        )
    finally:
        loop.close()
