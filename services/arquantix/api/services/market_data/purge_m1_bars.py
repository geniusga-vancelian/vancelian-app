"""
Purge old 1-minute candles from market_data_bars_1m.

Retention: 24 hours. Rows with open_time older than (now - 24h) are deleted.
Designed to run every 12 hours via the scheduler in main.py.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

RETENTION_HOURS = 24


def run_purge_m1_bars(session: Session) -> int:
    """Delete 1m bars older than RETENTION_HOURS.

    Returns the number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RETENTION_HOURS)
    result = session.execute(
        text("DELETE FROM public.market_data_bars_1m WHERE open_time < :cutoff"),
        {"cutoff": cutoff},
    )
    deleted = result.rowcount
    session.commit()
    logger.info("purge_m1_bars: deleted %d rows older than %s", deleted, cutoff.isoformat())
    return deleted
