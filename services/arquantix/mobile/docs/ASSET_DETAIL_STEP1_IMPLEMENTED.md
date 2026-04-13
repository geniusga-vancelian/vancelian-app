# Asset Detail — Step 1 Implemented

## Summary

The **Asset Detail** (crypto detail) screen has been implemented to use real backend market-data APIs: initial price and 24h change from REST, live price via WebSocket, and OHLC history for the chart with supported timeframes **1j** (5m candles) and **1s** (1h candles). Unsupported periods (1m, 1a, 5a) are shown but disabled.

---

## Files Created / Modified

### Created
- None (all changes are in existing feature structure).

### Modified

| File | Changes |
|------|--------|
| `lib/core/config.dart` | Added `quotesLatestUrl`, `candles5mUrl`, `candles1hUrl`. |
| `lib/features/markets/data/market_data_api.dart` | Added `CandleItem` model (OHLC + volume), `getCandles5m()`, `getCandles1h()`. |
| `lib/features/markets/data/market_display_utils.dart` | Added `tickerToProviderSymbol()` (e.g. BTC → BTCUSDT). |
| `lib/features/markets/presentation/widgets/chart_asset_module.dart` | Refactored: real candle data, 1j/1s only active, line chart from `close`, loading/error/empty states, period chips with disabled 1m/1a/5a. |
| `lib/features/markets/presentation/screens/crypto_detail_screen.dart` | Initial load via `market-summary`, WS for live price, chart timeframe state and candle loading, pass all data into `ChartAssetModule`; full-page and chart-area loading/error handling. |

---

## APIs Used

| API | Purpose | Auth (backend) |
|-----|---------|-----------------|
| **GET** `/api/market-data/market-summary?symbols=BTCUSDT` | Initial price, 24h change (abs/pct). | Public (no auth). |
| **GET** `/api/market-data/candles/5m?symbol=BTCUSDT&limit=300` | OHLC for 1-day view (1j). | May require auth. |
| **GET** `/api/market-data/candles/1h?symbol=BTCUSDT&limit=300` | OHLC for 1-week view (1s). | May require auth. |
| **WS** `/ws/market-data?symbols=BTCUSDT` | Live price updates. | No auth. |

- **quotes/latest** is not used in this step; initial data comes from **market-summary** (public).
- If candles endpoints return 401, the chart area shows an error state; no backend changes were made per scope.

---

## Supported Timeframes

| UI label | Backend | Supported |
|----------|---------|-----------|
| **1j** | `/candles/5m` | Yes |
| **1s** | `/candles/1h` | Yes |
| 1m | — | No (button disabled) |
| 1a | — | No (button disabled) |
| 5a | — | No (button disabled) |

- Switching between **1j** and **1s** reloads only the chart data (chart area loading state); the rest of the page stays stable.
- Other period buttons remain visible but are disabled and non-interactive.

---

## OHLC Handling

- Backend candle payload: `open_time`, `open`, `high`, `low`, `close`, `volume`.
- **Model**: `CandleItem` in `market_data_api.dart` with `openTime`, `open`, `high`, `low`, `close`, `volume`.
- **Chart**: Line chart built from **close** values only; data model is OHLC-ready for a future candlestick view.
- Code is structured so the same `CandleItem` list can later drive a candlestick painter without changing the API or loading logic.

---

## WebSocket Behavior

- On screen init, the app subscribes to **one symbol**: `/ws/market-data?symbols=BTCUSDT` (symbol derived from asset ticker via `tickerToProviderSymbol`).
- **Updated**: Only the **displayed current price**; 24h change values stay from the initial REST load (no live recalculation of 24h delta).
- No live chart streaming; chart data is loaded only via REST when the user switches timeframe.
- On dispose, the WebSocket is disconnected.

---

## Loading / Error States

- **Initial page**: Loading spinner + “Chargement…”; on error, message + “Réessayer” button.
- **Chart area**: Loading spinner + “Chargement du graphique…” when loading candles; error message and icon on API/network error; “Aucune donnée pour cette période” when the backend returns an empty candle list.
- No raw text dumps; all states use the app’s design system (typography, colors, spacing).

---

## Known Limitations

- **Candles auth**: Backend routes `/candles/5m` and `/candles/1h` may require auth; if the mobile client does not send a token, 401 will result and the chart will show the error state. Making these endpoints public (like market-summary) would require a backend change (out of scope for this step).
- **24h change**: Kept from initial REST response; not recomputed when the live price updates.
- **Candlestick view**: Only a line chart (close) is implemented; full OHLC candlestick rendering is left for a later step.
- **1m / 1a / 5a**: Shown in the UI but disabled; no fake or unsupported history.

---

## Navigation

- Existing navigation is reused: tap on a row in the Markets screen opens `CryptoDetailScreen(asset: asset)`.
- Route `/crypto/:slug` still resolves to `CryptoDetailScreen` (with `assetFromSlug` when no asset is passed).

---

## What Remains for Later

- Optional: make candles (and optionally quotes/latest) public on the backend for unauthenticated mobile use.
- Optional: true candlestick chart using the same `CandleItem` OHLC data.
- Optional: subtle “price just updated” effect when a new WS price arrives.
- Optional: refresh button or pull-to-refresh on the asset detail page to reload summary and chart.
