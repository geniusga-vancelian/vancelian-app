"""
WebSocket broadcast of latest market quotes (poll DB every 1s for real-time feel).
No auth in V1; document for V2.
"""
import asyncio
import logging
from typing import List, Optional
from urllib.parse import parse_qs

from fastapi import WebSocket
from sqlalchemy.orm import Session

from database import SessionLocal
from services.market_data.market_summary_repo import refresh_binance_quotes_for_provider_symbols
from services.market_data.quotes_repo import get_latest_quotes_by_provider_symbols, quotes_to_payload

logger = logging.getLogger(__name__)

BROADCAST_INTERVAL_SEC = 1.0


def _parse_symbols_from_query(websocket: WebSocket) -> Optional[List[str]]:
    """Parse and normalize symbols from WebSocket query string. Returns None if missing or empty."""
    query_bytes = websocket.scope.get("query_string") or b""
    query_string = query_bytes.decode("utf-8", errors="replace")
    parsed = parse_qs(query_string)
    raw = parsed.get("symbols", [])
    if not raw:
        return None
    # Normalize: strip, upper, dedupe (preserve order)
    seen = set()
    symbols = []
    for s in raw:
        for part in s.replace(",", " ").split():
            sym = part.strip().upper()
            if sym and sym not in seen:
                seen.add(sym)
                symbols.append(sym)
    return symbols if symbols else None


def _fetch_quotes_sync(session: Session, symbols: List[str]) -> list:
    """Sync DB fetch for use from async context via to_thread. Rafraîchit d'abord les quotes Binance en REST."""
    from services.market_data.fx import get_eurusdt_rate
    refresh_binance_quotes_for_provider_symbols(session, symbols)
    quotes = get_latest_quotes_by_provider_symbols(session, symbols)
    rate = float(get_eurusdt_rate(session, strict=False))
    return quotes_to_payload(quotes, eurusdt_rate=rate)


async def handle_market_data_ws(websocket: WebSocket) -> None:
    """
    Handle /ws/market-data: require symbols in query, then broadcast quotes every 1 second.
    Closes with error if symbols missing or empty. Sends {"quotes": []} when no data; does not close.
    """
    await websocket.accept()
    symbols = _parse_symbols_from_query(websocket)
    if not symbols:
        await websocket.close(code=4000, reason="Missing or empty query parameter: symbols (e.g. ?symbols=BTCUSDT,ETHUSDT)")
        return

    db = SessionLocal()
    try:
        while True:
            try:
                payload = await asyncio.to_thread(_fetch_quotes_sync, db, symbols)
                await websocket.send_json({"quotes": payload})
            except Exception as e:
                err_msg = str(e).lower()
                if "close" in err_msg or "disconnect" in err_msg or "connection" in err_msg:
                    break
                logger.exception("WebSocket market-data broadcast error: %s", e)
                try:
                    await websocket.close(code=1011, reason="Server error")
                except Exception:
                    pass
                return
            await asyncio.sleep(BROADCAST_INTERVAL_SEC)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        err_msg = str(e).lower()
        if "disconnect" not in err_msg and "closed" not in err_msg and "connection" not in err_msg:
            logger.warning("WebSocket market-data closed: %s", e)
    finally:
        db.close()
