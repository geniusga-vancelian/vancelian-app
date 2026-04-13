# Price Alert Engine — Hardening Report

## 1. Notification Batching

### Problem
Individual `INSERT` per triggered alert does not scale when 100k alerts trigger simultaneously at the same price level.

### Solution
Created `NotificationDispatcher` (`api/services/notifications/dispatcher.py`):

- **Thread-safe queue** with `deque` + `threading.Lock`
- **Background flush thread** drains the queue every 500ms
- **Max batch size: 500** — single `db.commit()` per batch
- **Graceful shutdown** — flushes remaining items on stop
- **Internal stats** — `enqueued`, `flushed`, `failures` counters

```
Engine._process_triggered()
    └─ dispatcher.enqueue(client_id, type, title, body, payload)
           └─ [background thread] _flush_batch() → DB INSERT x500 → commit
```

The engine no longer writes notifications inline — it enqueues them. This decouples trigger latency from notification write latency.

## 2. Debounce / Cooldown

### Problem
Price flapping (oscillating around a target) could trigger the same alert-level repeatedly if the alert was re-created.

### Solution
Added to `price_alerts` table (migration `070`):

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `cooldown_seconds` | Integer | 0 | Minimum seconds between triggers |
| `last_triggered_at` | DateTime tz | null | Timestamp of last trigger |

Engine logic in `_process_triggered()`:

```python
if alert.cooldown_seconds > 0 and alert.last_triggered_at is not None:
    elapsed = (now - alert.last_triggered_at).total_seconds()
    if elapsed < alert.cooldown_seconds:
        metrics.record_cooldown_skip()
        continue
```

Default cooldown is 0 (disabled). API accepts `cooldown_seconds` (0–86400) on creation.

## 3. Price Source Hardening

### Problem
All alerts previously triggered on MID price only, regardless of `price_source` field.

### Solution
Now stores **three separate price tracks** in Redis:

```
prices:{ASSET}:last_bid
prices:{ASSET}:last_ask
prices:{ASSET}:last_mid
```

Engine checks **each source independently**:

```python
triggered += self._check_source(asset, "mid", prev_mid, mid, db_factory)
triggered += self._check_source(asset, "bid", prev_bid, bid, db_factory)
triggered += self._check_source(asset, "ask", prev_ask, ask, db_factory)
```

In `_process_triggered`, alerts are filtered by `price_source == source`:

```python
alert = db.query(PriceAlert).filter(
    PriceAlert.id == aid,
    PriceAlert.status == "active",
    PriceAlert.price_source == source,  # ← only matching source
).first()
```

This ensures:
- **BUY order triggers** respond to ASK crossing
- **SELL order triggers** respond to BID crossing
- **Simple alerts** respond to MID crossing

## 4. Redis Scaling Prep

### Problem
A single sorted set per (asset, direction) becomes a bottleneck at extreme scale.

### Solution
Hash-bucket sharding across `NUM_BUCKETS = 4`:

```
alerts:{ASSET}:{direction}:{bucket}
  where bucket = hash(alert_id) % 4
```

All cache operations (add, remove, load, query) now iterate across all buckets:

```python
def get_crossed_alert_ids(r, asset, direction, low, high):
    ids = []
    for bucket in range(NUM_BUCKETS):
        key = _direction_key(asset, direction, bucket)
        raw = r.zrangebyscore(key, min=low, max=high)
        ids.extend(raw)
    return ids
```

This distributes write load and allows future migration to Redis Cluster where keys can be distributed across slots.

## 5. Order Execution Safety

### Problem
Phase 2 order execution must be idempotent — no double execution.

### Solution
Added `execution_status` column (migration `070`):

| Value | Meaning |
|-------|---------|
| `null` | Not an order trigger (simple alert) |
| `pending` | Order queued, not yet executed |
| `executed` | Order successfully placed |
| `failed` | Order execution failed |

In engine:

```python
if alert.action_type == "order" and alert.order_payload:
    alert.execution_status = "pending"
    # ...
    self._execute_order_hook(alert, db)
```

The hook checks `execution_status != "pending"` before proceeding:

```python
def _execute_order_hook(alert, db):
    if alert.execution_status != "pending":
        return  # idempotent guard
```

Additionally, `SELECT ... FOR UPDATE SKIP LOCKED` prevents concurrent workers from processing the same alert.

## 6. Observability

### Problem
No visibility into engine performance, trigger rates, or failure patterns.

### Solution
Created `AlertMetrics` singleton (`api/services/price_alerts/metrics.py`):

| Metric | Type | Description |
|--------|------|-------------|
| `alerts_triggered_total` | Counter | Total alerts triggered since startup |
| `alerts_per_asset` | Counter dict | Triggered count by asset (BTC, ETH...) |
| `ticks_processed` | Counter | Price ticks processed |
| `crossings_detected` | Counter | Level crossings detected |
| `cooldown_skips` | Counter | Alerts skipped due to cooldown |
| `notification_failures` | Counter | NotificationDispatcher write failures |
| `redis_errors` | Counter | Redis communication errors |
| `trigger_latency_avg_ms` | Gauge | Average trigger processing latency |
| `trigger_latency_p99_ms` | Gauge | P99 trigger processing latency |

Exposed via `GET /api/app/alerts/metrics`:

```json
{
  "alerts_triggered_total": 42,
  "alerts_per_asset": {"BTC": 30, "ETH": 12},
  "ticks_processed": 150000,
  "trigger_latency_avg_ms": 1.23,
  "trigger_latency_p99_ms": 4.56,
  "notification_dispatcher": {
    "enqueued": 42,
    "flushed": 42,
    "failures": 0
  }
}
```

`LatencyTimer` context manager measures per-batch processing time.

## 7. Fail-Safe

### Problem
Redis downtime or errors must never block price ingestion.

### Solution
Multi-layer protection:

1. **`get_redis()` returns `None`** if Redis is unreachable → engine skips entirely
2. **`_check_price_alerts()` wraps engine call** in `try/except` → ingestion continues
3. **All cache functions accept `r=None`** → return empty/no-op
4. **`get_alert_engine()` returns `None`** if Redis was unavailable at startup
5. **Redis errors increment `redis_errors` metric** for monitoring

```python
def _check_price_alerts(pending):
    try:
        engine = get_alert_engine()
        if engine is None:
            return
        engine.on_price_batch(pending, SessionLocal)
    except Exception:
        get_metrics().record_redis_error()
        logger.debug("Price alert check skipped")
```

## 8. Files Modified/Created

| File | Action |
|------|--------|
| `api/alembic/versions/070_harden_price_alerts.py` | **New**: migration — cooldown, execution_status, metadata_ |
| `api/services/price_alerts/models.py` | **Modified**: added cooldown_seconds, last_triggered_at, execution_status, metadata_ |
| `api/services/price_alerts/cache.py` | **Rewritten**: hash-bucket sharding, per-source price tracking |
| `api/services/price_alerts/engine.py` | **Rewritten**: multi-source crossing, cooldown, batched notifications, metrics |
| `api/services/price_alerts/metrics.py` | **New**: AlertMetrics + LatencyTimer |
| `api/services/price_alerts/router.py` | **Modified**: cooldown_seconds in create, /metrics endpoint |
| `api/services/notifications/dispatcher.py` | **New**: NotificationDispatcher (queue + batch flush) |
| `api/services/market_data/binance_ws_ingestion.py` | **Modified**: redis_error metric on failure |
| `api/main.py` | **Modified**: init_dispatcher at startup |
| `mobile/lib/features/alerts/domain/models/price_alert.dart` | **Modified**: cooldownSeconds, executionStatus |

## 9. Validation Matrix

| Test Case | Status |
|-----------|--------|
| 100k alerts at same price → single batch trigger | ✅ Designed (ZRANGEBYSCORE + batch notify) |
| Price flapping → single trigger (cooldown) | ✅ Implemented (cooldown_seconds) |
| Cooldown window respected | ✅ Checked in `_process_triggered` |
| Order not executed twice | ✅ `execution_status` + `SKIP LOCKED` |
| Redis down → ingestion continues | ✅ Multi-layer try/except + None checks |
| BUY trigger uses ASK, SELL uses BID | ✅ Per-source crossing detection |
| Latency tracked per trigger batch | ✅ LatencyTimer + metrics snapshot |
| Notification failures tracked | ✅ dispatcher.stats["failures"] |

## 10. Architecture Summary

```
Binance WS tick
      │
      ▼
_flush_pending()
  ├─ upsert_latest_quote() → PostgreSQL
  └─ _check_price_alerts() [fail-safe wrapper]
         │
         ▼
   PriceAlertEngine.on_price_batch()
     ├─ get_and_set_price(bid/ask/mid) → Redis
     ├─ _check_source("mid") → ZRANGEBYSCORE x4 buckets
     ├─ _check_source("bid") → ZRANGEBYSCORE x4 buckets
     ├─ _check_source("ask") → ZRANGEBYSCORE x4 buckets
     │
     └─ _process_triggered()
          ├─ SELECT ... FOR UPDATE SKIP LOCKED
          ├─ Cooldown check
          ├─ UPDATE status='triggered'
          ├─ ZREM from Redis
          ├─ NotificationDispatcher.enqueue() [non-blocking]
          ├─ _execute_order_hook() [Phase 2, idempotent]
          ├─ metrics.record_trigger()
          └─ db.commit()

NotificationDispatcher [background thread]
  └─ every 500ms: drain queue → INSERT batch (≤500) → commit
```
