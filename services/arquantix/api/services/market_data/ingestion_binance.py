"""
Binance latest-quote ingestion: load instruments, fetch tickers, upsert into market_data_latest_quotes.
Runs as a separate process/script; does not depend on FastAPI lifecycle.
Caller opens the session; this module commits once per cycle.
"""
import logging
from typing import List, Tuple

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.binance_client import fetch_ticker
from services.market_data.quotes_repo import upsert_latest_quote

logger = logging.getLogger(__name__)

PROVIDER = "binance"


def load_binance_instruments(session: Session) -> List[Tuple[int, str]]:
    """
    Load instrument_id and provider_symbol for all Binance-enabled instruments.
    Filter: provider == "binance" and is_active is truthy (DB stores "true"/"false" string).
    Returns list of (instrument_id, provider_symbol).
    """
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


def run_one_cycle(session: Session) -> Tuple[int, int, List[str]]:
    """
    Run one ingestion cycle: load Binance instruments, fetch ticker for each, upsert, commit once.
    Returns (updated_count, failure_count, list of error messages).
    """
    instruments = load_binance_instruments(session)
    if not instruments:
        logger.info("No Binance instruments found (provider=binance, is_active=true)")
        return 0, 0, []

    updated = 0
    failures = []
    for instrument_id, provider_symbol in instruments:
        try:
            quote = fetch_ticker(provider_symbol)
            if not quote:
                failures.append(f"{provider_symbol}: no data from Binance")
                continue
            upsert_latest_quote(
                session,
                instrument_id=instrument_id,
                provider=PROVIDER,
                provider_symbol=quote.get("provider_symbol") or provider_symbol,
                last_price=quote["last_price"],
                bid_price=quote.get("bid_price"),
                ask_price=quote.get("ask_price"),
                volume=quote.get("volume"),
                quote_time=quote.get("quote_time"),
            )
            updated += 1
        except Exception as e:  # noqa: BLE001
            msg = f"{provider_symbol}: {e!s}"
            failures.append(msg)
            logger.exception("Ingestion failed for %s", provider_symbol)

    if updated > 0 or not failures:
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            logger.exception("Commit failed: %s", e)
            return 0, len(instruments), [f"Commit failed: {e!s}"]
    else:
        # All failed; no commit
        session.rollback()

    return updated, len(failures), failures
