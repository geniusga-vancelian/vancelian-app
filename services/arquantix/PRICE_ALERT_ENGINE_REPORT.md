# Price Alert & Trigger Engine — Implementation Report

## 1. Architecture

```
Binance WS bookTicker
        │
        ▼
 _flush_pending()
   ├─ upsert_latest_quote()   → PostgreSQL
   └─ _check_price_alerts()   → PriceAlertEngine.on_price_batch()
                                    │
                                    ▼
                              Redis ZRANGEBYSCORE
                              alerts:{ASSET}:up / :down
                                    │
                                    ▼
                            _process_triggered()
                              ├─ ZREM (Redis, atomic)
                              ├─ UPDATE price_alerts SET status='triggered'
                              ├─ INSERT notifications
                              └─ [Phase 2: OrderExecutionEngine hook]
```

**Key design decisions:**

- **Indexed by asset, not per-user** — O(log N + K) per tick, K = matched alerts
- **Redis Sorted Sets** — `score = target_price`, `member = alert_id`
- **Event-driven, not polling** — triggered from the existing Binance WS flush pipeline
- **Fail-safe** — alert engine errors never block price ingestion (`try/except` wrapper)
- **Graceful degradation** — if Redis is unavailable, the engine disables itself

## 2. Redis Design

| Key | Type | Score | Member |
|-----|------|-------|--------|
| `alerts:{ASSET}:up` | Sorted Set | `target_price` | `alert_id` (UUID str) |
| `alerts:{ASSET}:down` | Sorted Set | `target_price` | `alert_id` (UUID str) |
| `prices:{ASSET}:last_mid` | String | — | previous mid price |

**Crossing detection algo:**

```
CROSS UP  (price rose):   ZRANGEBYSCORE alerts:BTC:up   prev_mid  current_mid
CROSS DOWN (price fell):  ZRANGEBYSCORE alerts:BTC:down  current_mid  prev_mid
```

Gap handling: if price jumps 98k → 102k, `ZRANGEBYSCORE 98000 102000` catches **all** intermediate levels.

## 3. Trigger Logic & Idempotence

Three-layer idempotence guarantees no double trigger:

1. **Redis ZREM** — atomic removal prevents parallel pickup of the same alert
2. **DB status check** — `WHERE status='active'` in UPDATE prevents double write
3. **Notification insert** — only on successful DB transition to `triggered`

## 4. Database Schema

### `price_alerts`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `uuid.uuid4` |
| `client_id` | UUID FK → `pe_clients.id` | |
| `asset` | String(20) | BTC, ETH, etc. |
| `target_price` | Numeric(20,8) | |
| `direction` | String(10) | `up` / `down` |
| `price_source` | String(10) | `bid` / `ask` / `mid` |
| `status` | String(20) | `active` / `triggered` / `cancelled` |
| `action_type` | String(20) | `alert` (Phase 1) / `order` (Phase 2) |
| `order_payload` | JSONB nullable | Phase 2: `{side, amount, type}` |
| `triggered_at` | DateTime tz | When triggered |
| `triggered_price` | Numeric(20,8) | Actual price at trigger |

Index: `(client_id, asset, status)`

### `notifications`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `client_id` | UUID FK → `pe_clients.id` | |
| `type` | String(30) | `price_alert`, `order_executed`, etc. |
| `title` | String(200) | Human-readable |
| `body` | Text | Optional detail |
| `payload` | JSONB | Machine-readable context |
| `is_read` | Boolean | Default `false` |
| `created_at` | DateTime tz | |

Index: `(client_id, is_read)`

Migration: `069_add_price_alerts_and_notifications.py`

## 5. API Endpoints

### Price Alerts (`/api/app/alerts`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/app/alerts` | Create alert |
| GET | `/api/app/alerts` | List alerts (optional `?status=active`) |
| DELETE | `/api/app/alerts/{id}` | Cancel alert |

### Notifications (`/api/app/notifications`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/app/notifications` | List (paginated: `?limit=50&offset=0`) |
| GET | `/api/app/notifications/unread-count` | Badge count |
| POST | `/api/app/notifications/{id}/read` | Mark one as read |
| POST | `/api/app/notifications/read-all` | Mark all as read |

## 6. Scalability

| Scenario | Complexity |
|----------|-----------|
| 100k users, same price level | 1 Redis query + 1 batch DB update |
| Price gap (98k → 102k) | 1 ZRANGEBYSCORE catches all levels |
| Duplicate tick (same price) | Skipped (`abs(mid - prev) < 1e-10`) |
| Redis down | Engine disables gracefully, prices still ingested |
| DB error during trigger | Rollback, alert stays active in Redis for retry |

## 7. Flutter Integration

### Data Layer
- `PriceAlertsApi` — CRUD for alerts
- `NotificationsApi` — list, unread count, mark read

### Models
- `PriceAlert` — immutable data class with `fromJson`
- `AppNotification` — immutable data class with `fromJson`

### UI
- **NotificationCenterScreen** — replaced mocked data with API-backed list, grouped by date
- **AlertsListScreen** — active/triggered/cancelled sections with cancel action
- **CreateAlertBottomSheet** — asset + target price + direction selector
- **Home bell icon** — shows unread badge dot via `_unreadNotificationCount`

### Next.js Proxy Routes
- `/api/mobile/flutter/alerts/*` → `/api/app/alerts/*`
- `/api/mobile/flutter/notifications/*` → `/api/app/notifications/*`

## 8. Future Extension (Phase 2 — Orders)

The schema and engine are ready for automatic order execution:

```python
# In PriceAlert model:
action_type = "order"
order_payload = {"side": "buy", "amount": 1000, "type": "market"}

# In engine._process_triggered():
if alert.action_type == "order" and alert.order_payload:
    # → OrderExecutionEngine.execute(order_payload)
    pass
```

This same infrastructure supports:
- **Stop Loss** — `direction=down`, `action_type=order`, `side=sell`
- **Take Profit** — `direction=up`, `action_type=order`, `side=sell`
- **Limit Orders** — `direction=down`, `action_type=order`, `side=buy`
- **Copy Trading** — alert triggers replicated order
- **Algo Trading** — chained alerts with complex payloads

## 9. Files Created/Modified

| File | Action |
|------|--------|
| `docker-compose.arquantix.yml` | Modified: added `arquantix-redis` service |
| `.env.arquantix.example` | Modified: added `REDIS_URL` |
| `api/requirements.txt` | Modified: added `redis>=5.0` |
| `api/services/redis_client.py` | **New**: Redis connection singleton |
| `api/services/price_alerts/__init__.py` | **New**: package |
| `api/services/price_alerts/models.py` | **New**: PriceAlert model |
| `api/services/price_alerts/cache.py` | **New**: Redis sorted-set cache manager |
| `api/services/price_alerts/engine.py` | **New**: PriceAlertEngine + singleton |
| `api/services/price_alerts/router.py` | **New**: REST endpoints |
| `api/services/notifications/__init__.py` | **New**: package |
| `api/services/notifications/models.py` | **New**: Notification model |
| `api/services/notifications/router.py` | **New**: REST endpoints |
| `api/alembic/versions/069_...` | **New**: migration |
| `api/services/market_data/binance_ws_ingestion.py` | Modified: added `_check_price_alerts` hook |
| `api/main.py` | Modified: registered routers + startup cache loader |
| `web/src/app/api/mobile/flutter/alerts/route.ts` | **New**: Next.js proxy |
| `web/src/app/api/mobile/flutter/alerts/[alertId]/route.ts` | **New**: Next.js proxy |
| `web/src/app/api/mobile/flutter/notifications/route.ts` | **New**: Next.js proxy |
| `web/src/app/api/mobile/flutter/notifications/unread-count/route.ts` | **New**: Next.js proxy |
| `web/src/app/api/mobile/flutter/notifications/[notificationId]/read/route.ts` | **New**: Next.js proxy |
| `web/src/app/api/mobile/flutter/notifications/read-all/route.ts` | **New**: Next.js proxy |
| `mobile/lib/core/config.dart` | Modified: added alert/notification URLs |
| `mobile/lib/features/alerts/domain/models/price_alert.dart` | **New**: model |
| `mobile/lib/features/alerts/data/price_alerts_api.dart` | **New**: API client |
| `mobile/lib/features/alerts/presentation/screens/create_alert_bottom_sheet.dart` | **New**: create alert UI |
| `mobile/lib/features/alerts/presentation/screens/alerts_list_screen.dart` | **New**: alert list UI |
| `mobile/lib/features/notifications/domain/models/app_notification.dart` | **New**: model |
| `mobile/lib/features/notifications/data/notifications_api.dart` | **New**: API client |
| `mobile/lib/features/notifications/presentation/screens/notification_center_screen.dart` | **Replaced**: mocked → API-backed |
| `mobile/lib/features/home/presentation/screens/home_screen.dart` | Modified: unread badge |

## 10. Status

| Component | Status |
|-----------|--------|
| Redis infrastructure | ✅ Ready |
| Database models + migration | ✅ Ready |
| Redis cache loader | ✅ Ready |
| Trigger engine (crossing detection) | ✅ Ready |
| Binance WS hook | ✅ Ready |
| API endpoints (alerts + notifications) | ✅ Ready |
| Next.js proxy routes | ✅ Ready |
| Flutter models + API clients | ✅ Ready |
| Flutter UI (alerts + notifications) | ✅ Ready |
| Unread badge on home | ✅ Ready |
| Phase 2 order hook | 🔧 Stub ready |
