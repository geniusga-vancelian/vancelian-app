"""Redis sorted-set cache for active price alerts.

Keys (with hash-bucket sharding for future horizontal scaling):
  alerts:{ASSET}:up:{bucket}    — sorted set, score = target_price, member = alert_id
  alerts:{ASSET}:down:{bucket}  — sorted set, score = target_price, member = alert_id

Price tracking (per-source for bid/ask/mid crossing):
  prices:{ASSET}:last_bid — string
  prices:{ASSET}:last_ask — string
  prices:{ASSET}:last_mid — string

Bucket count is configurable (NUM_BUCKETS). Default 4.
"""
import hashlib
import logging
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

NUM_BUCKETS = 4


def _bucket_for(alert_id: str) -> int:
    # hashlib is deterministic across processes (unlike Python's hash())
    return int(hashlib.sha256(alert_id.encode()).hexdigest(), 16) % NUM_BUCKETS


def _direction_key(asset: str, direction: str, bucket: int) -> str:
    return f"alerts:{asset.upper()}:{direction}:{bucket}"


def _price_key(asset: str, source: str) -> str:
    return f"prices:{asset.upper()}:last_{source}"


# ---------------------------------------------------------------------------
# Single-alert operations
# ---------------------------------------------------------------------------

def add_alert_to_cache(r, alert) -> None:
    if r is None:
        return
    bucket = _bucket_for(str(alert.id))
    key = _direction_key(alert.asset, alert.direction, bucket)
    r.zadd(key, {str(alert.id): float(alert.target_price)})


def remove_alert_from_cache(r, alert_id: str, asset: str, direction: str) -> None:
    """Remove alert from ALL buckets to handle legacy hash-drift entries."""
    if r is None:
        return
    pipe = r.pipeline(transaction=False)
    for bucket in range(NUM_BUCKETS):
        key = _direction_key(asset, direction, bucket)
        pipe.zrem(key, alert_id)
    pipe.execute()


# ---------------------------------------------------------------------------
# Bulk load
# ---------------------------------------------------------------------------

def load_all_active_alerts(r, db: Session) -> int:
    """Warm the Redis cache from DB on startup. Returns count loaded.

    Purges all existing alert keys first to avoid stale/duplicate entries
    caused by hash-seed drift between processes.
    """
    if r is None:
        logger.warning("Redis unavailable — alert cache not loaded")
        return 0

    from services.price_alerts.models import PriceAlert

    _purge_all_alert_keys(r)

    alerts = db.query(PriceAlert).filter(PriceAlert.status == "active").all()
    if not alerts:
        logger.info("No active price alerts to load into Redis")
        return 0

    pipe = r.pipeline(transaction=False)
    for a in alerts:
        bucket = _bucket_for(str(a.id))
        key = _direction_key(a.asset, a.direction, bucket)
        pipe.zadd(key, {str(a.id): float(a.target_price)})
    pipe.execute()
    logger.info("Loaded %d active price alerts into Redis (%d buckets)", len(alerts), NUM_BUCKETS)
    return len(alerts)


def _purge_all_alert_keys(r) -> None:
    """Delete all alerts:* sorted-set keys to ensure a clean slate."""
    cursor = 0
    deleted = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match="alerts:*", count=500)
        if keys:
            r.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break
    if deleted:
        logger.info("Purged %d stale alert cache keys from Redis", deleted)


# ---------------------------------------------------------------------------
# Crossing detection (multi-bucket, multi-source)
# ---------------------------------------------------------------------------

def get_crossed_alert_ids_sorted(
    r,
    asset: str,
    direction: str,
    low: float,
    high: float,
) -> list[tuple[str, float]]:
    """Return (alert_id, score) pairs sorted deterministically.

    CROSS UP  → sorted by target_price ASC  (lowest level triggered first)
    CROSS DOWN → sorted by target_price DESC (highest level triggered first)
    """
    if r is None:
        return []

    pairs: list[tuple[str, float]] = []
    for bucket in range(NUM_BUCKETS):
        key = _direction_key(asset, direction, bucket)
        raw = r.zrangebyscore(key, min=low, max=high, withscores=True)
        pairs.extend(raw)

    reverse = direction == "down"
    pairs.sort(key=lambda x: x[1], reverse=reverse)
    return pairs


def get_crossed_alert_ids(
    r,
    asset: str,
    direction: str,
    low: float,
    high: float,
) -> list[str]:
    """Backward-compatible: returns just IDs (sorted deterministically)."""
    return [aid for aid, _ in get_crossed_alert_ids_sorted(r, asset, direction, low, high)]


# ---------------------------------------------------------------------------
# Price tracking (per-source)
# ---------------------------------------------------------------------------

def get_and_set_price(r, asset: str, source: str, price: float) -> Optional[float]:
    """Atomically get previous price for source and set new. Returns previous or None."""
    if r is None:
        return None
    key = _price_key(asset, source)
    prev_raw = r.getset(key, str(price))
    if prev_raw is None:
        return None
    try:
        return float(prev_raw)
    except (TypeError, ValueError):
        return None


def get_and_set_last_mid(r, asset: str, mid: float) -> Optional[float]:
    """Backward-compatible wrapper."""
    return get_and_set_price(r, asset, "mid", mid)


# ---------------------------------------------------------------------------
# Notification dedup
# ---------------------------------------------------------------------------

_DEDUP_TTL_SEC = 2


def check_notif_dedup(r, client_id, asset: str, direction: str) -> bool:
    """Return True if a notification was already sent for this key within the dedup window.

    Sets the key with TTL if not present (returns False → proceed).
    Returns True → skip duplicate.
    """
    if r is None:
        return False
    key = f"notif_dedup:{client_id}:{asset.upper()}:{direction}"
    already = r.set(key, "1", nx=True, ex=_DEDUP_TTL_SEC)
    return already is None  # None means key already existed → duplicate
