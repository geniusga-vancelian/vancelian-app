# Frontend — Backtest & Market Data UI

## Architecture

**Framework** : Next.js 14+ (App Router)

**Pages** :
- `/admin/backtests` : Builder + Results + Market Data panel
- `/admin/diagnostics` : Diagnostic checks

**Pattern** : Next.js API routes (proxy) → FastAPI backend

---

## Pages

### `/admin/backtests`

**Fichier** : `web/src/app/admin/backtests/page.tsx`

**Composants** :
- `MarketDataBackfill` : Panel backfill market data
- `BacktestBuilder` : Builder backtest (sélection instruments, dates, stratégie)
- `BacktestResults` : Résultats (chart, stats, weights)

**État** :
- `lastRunId` : ID dernier backtest exécuté
- `historyPreview` : Données performance historique (sans backtest)

**Flux** :
1. User sélectionne instruments + dates + stratégie
2. Click "Run Backtest" → `POST /api/backtests/run` → `setLastRunId(runId)`
3. Ou click "Voir historiques" → `GET /api/market-data/performance` → `setHistoryPreview(data)`
4. `BacktestResults` affiche résultats (backtest ou historique)

---

### `/admin/diagnostics`

**Fichier** : `web/src/app/admin/diagnostics/page.tsx`

**Fonctionnalités** :
- "Run Quick Diagnostic" : `POST /api/diagnostics/market-backtest/run`
- "Auth Probe" : `GET /api/auth/probe`
- "Who am I?" : `GET /api/diagnostics/whoami`
- "JWT Debug" : `POST /api/diagnostics/jwt-debug`
- "Auth Trace" : `POST /api/diagnostics/auth-trace`

**Affichage** : JSON report (checks PASS/FAIL, détails, erreurs).

---

## Composants

### `MarketDataBackfill`

**Fichier** : `web/src/components/backtests/MarketDataBackfill.tsx`

**Fonctionnalités** :

1. **Validate Alpha Vantage (7 assets)** :
   - Button → `POST /api/market-data/validate-provider`
   - Affiche tableau résultats (OK/FAIL par symbole)

2. **Refresh Missing List** :
   - Button → `GET /api/market-data/missing`
   - Affiche liste instruments sans bars

3. **Backfill all missing instruments** :
   - Dropdown jours : 90 / 180 / 365 / 730
   - Button → `POST /api/market-data/backfill-missing`
   - Progress bar : `processed_count / missing_before`
   - Liste scrollable : instruments avec status (ok/error), bars_added, error
   - Refresh missing list après completion

**État** :
- `missingInstruments` : Liste instruments sans bars
- `isBackfilling` : Loading state
- `backfillProgress` : Liste résultats par instrument
- `backfillSummary` : Résumé final
- `validationResults` : Résultats validation Alpha Vantage

**UI** :
- Card avec header (titre + boutons)
- Tableau validation (si `validationResults` présent)
- Progress bar + liste instruments (si `isBackfilling`)
- Résumé backfill (si `backfillSummary` présent)
- Liste instruments manquants (scrollable)

---

### `BacktestBuilder`

**Fichier** : `web/src/components/backtests/BacktestBuilder.tsx`

**Fonctionnalités** :

1. **Sélection instruments** :
   - Multi-select checkboxes
   - Charge via `GET /api/backtests/instruments`
   - Affiche symbol, name, asset_class

2. **Date range** :
   - Input `start_date` (YYYY-MM-DD)
   - Input `end_date` (YYYY-MM-DD)
   - Validation : `end_date > start_date`

3. **Strategy** :
   - Select : `equal_weight` ou `momentum`
   - Si `momentum` : Input `lookback_days` (1-252)

4. **Rebalance** :
   - Select : `daily`, `weekly`, `monthly`

5. **Costs** :
   - Input `fees_bps` (0-1000)
   - Input `slippage_bps` (0-1000)

6. **Weekend Trading** :
   - Checkbox `allow_weekend_trading`

7. **Actions** :
   - Button "Run Backtest" → `POST /api/backtests/run` → `onBacktestComplete(runId)`
   - Button "Voir historiques" → `GET /api/market-data/performance` → `onHistoryPreview(data)`

**État** :
- `instruments` : Liste instruments disponibles
- `selectedInstrumentIds` : IDs sélectionnés
- `startDate`, `endDate` : Dates
- `strategyType` : `"equal_weight"` ou `"momentum"`
- `lookbackDays` : Si momentum
- `rebalance` : `"daily"` | `"weekly"` | `"monthly"`
- `feesBps`, `slippageBps` : Costs
- `allowWeekendTrading` : Boolean
- `isLoading`, `isLoadingHistory` : Loading states

**Validation** :
- Au moins 1 instrument sélectionné
- `end_date > start_date`
- Si `momentum` : `lookback_days` requis

---

### `BacktestResults`

**Fichier** : `web/src/components/backtests/BacktestResults.tsx`

**Props** :
- `runId` : `number | null` (ID backtest)
- `historyPreview` : `PerformanceResponse | null` (historique sans backtest)

**Fonctionnalités** :

1. **Mode** :
   - Si `runId` : Affiche résultats backtest
   - Si `historyPreview` : Affiche historique (base100)

2. **Tabs** :
   - **Chart** : Graphique NAV base100 (portfolio + benchmarks)
   - **Stats** : Tableau métriques
   - **Weights** (debug) : Poids par jour (si backtest)

3. **Chart** :
   - Recharts multi-line
   - Ligne portfolio (NAV base100)
   - Lignes benchmarks (instruments base100)
   - Legend clickable (show/hide)
   - Layout : `single` ou `multiples`

4. **Stats** :
   - Si backtest : Métriques portfolio + instruments
   - Si historique : Stats par instrument (total_return, maxDD, vol_annual)

**État** :
- `detail` : `BacktestDetailResponse | null`
- `series` : `SeriesResponse | null`
- `isLoading` : Loading state
- `layout` : `'single'` | `'multiples'`

**Chargement** :
- Si `runId` : `GET /api/backtests/{runId}` + `GET /api/backtests/{runId}/series`
- Si `historyPreview` : Utilise données directement

---

### `BacktestChart`

**Fichier** : `web/src/components/backtests/BacktestChart.tsx`

**Props** :
- `portfolioSeries` : `List[PortfolioBar>`
- `instrumentSeries : `List[InstrumentSeries]`
- `layout` : `'single'` | `'multiples'`

**Librairie** : Recharts

**Graphique** :
- `LineChart` avec `XAxis` (date), `YAxis` (base100)
- Ligne portfolio : `nav_base100`
- Lignes instruments : `base100` (une par instrument)
- Legend clickable (show/hide)
- Tooltip avec date + valeurs

---

### `BacktestStatsTable`

**Fichier** : `web/src/components/backtests/BacktestStatsTable.tsx`

**Props** :
- `portfolioMetrics` : `Dict[str, float]`
- `instrumentMetrics` : `List[Dict]` (par instrument)

**Affichage** :
- Tableau métriques portfolio (CAGR, Sharpe, MaxDD, etc.)
- Tableau métriques instruments (comparaison)

---

### `HistoryChart`

**Fichier** : `web/src/components/backtests/HistoryChart.tsx`

**Props** :
- `performance` : `PerformanceResponse`

**Graphique** :
- Recharts multi-line
- Une ligne par instrument (base100)
- Pas de ligne portfolio (historique uniquement)

---

### `HistoryStatsTable`

**Fichier** : `web/src/components/backtests/HistoryStatsTable.tsx`

**Props** :
- `performance` : `PerformanceResponse`

**Affichage** :
- Tableau stats par instrument (total_return, maxDD, vol_annual)

---

## Proxies API (Next.js Routes)

### Pattern général

**Emplacement** : `web/src/app/api/{module}/{endpoint}/route.ts`

**Pattern** :
1. Extraire session cookie : `getSessionFromCookie()`
2. Vérifier session : `session && session.userEmail`
3. Signer JWT : `jwt.sign({ sub: session.userEmail, email: session.userEmail }, secret)`
4. Appeler backend : `fetch(buildBackendUrl(...), { Authorization: Bearer {token} })`
5. Lire réponse : `await response.text()` puis `JSON.parse()`
6. Retourner : `NextResponse.json(data)`

**Gestion erreurs** :
- Si `!session` : `401 Unauthorized`
- Si `!response.ok` : Retourner `{ error, backend_status, backend_body }` avec status code backend

---

### `/api/market-data/missing`

**Fichier** : `web/src/app/api/market-data/missing/route.ts`

**Méthode** : `GET`

**Backend** : `GET /api/market-data/missing`

**Retour** : `List[MissingInstrumentResponse]`

---

### `/api/market-data/backfill-missing`

**Fichier** : `web/src/app/api/market-data/backfill-missing/route.ts`

**Méthode** : `POST`

**Body** : `{ days, symbols?, force }`

**Backend** : `POST /api/market-data/backfill-missing`

**Retour** : `BackfillMissingResponse`

---

### `/api/market-data/validate-provider`

**Fichier** : `web/src/app/api/market-data/validate-provider/route.ts`

**Méthode** : `POST`

**Body** : `{ symbols, years }`

**Backend** : `POST /api/market-data/validate-provider`

**Retour** : `ValidateProviderResponse`

---

### `/api/market-data/performance`

**Fichier** : `web/src/app/api/market-data/performance/route.ts`

**Méthode** : `GET`

**Query params** : `instrument_ids`, `start`, `end`, `base`

**Backend** : `GET /api/market-data/performance`

**Retour** : `PerformanceResponse`

---

### `/api/backtests/instruments`

**Fichier** : `web/src/app/api/backtests/instruments/route.ts`

**Méthode** : `GET`

**Backend** : `GET /api/backtests/instruments`

**Retour** : `List[InstrumentInfo]`

---

### `/api/backtests/run`

**Fichier** : `web/src/app/api/backtests/run/route.ts`

**Méthode** : `POST`

**Body** : `BacktestCreateRequest`

**Backend** : `POST /api/backtests/run`

**Retour** : `BacktestRunResponse`

---

### `/api/backtests/{run_id}`

**Fichier** : `web/src/app/api/backtests/[run_id]/route.ts`

**Méthode** : `GET`

**Backend** : `GET /api/backtests/{run_id}`

**Retour** : `BacktestDetailResponse`

---

### `/api/backtests/{run_id}/series`

**Fichier** : `web/src/app/api/backtests/[run_id]/series/route.ts`

**Méthode** : `GET`

**Backend** : `GET /api/backtests/{run_id}/series`

**Retour** : `SeriesResponse`

---

### `/api/diagnostics/market-backtest/run`

**Fichier** : `web/src/app/api/diagnostics/market-backtest/run/route.ts`

**Méthode** : `POST`

**Body** : `{ mode: "quick" | "full", start_date?, end_date? }`

**Backend** : `POST /api/diagnostics/market-backtest/run`

**Retour** : Diagnostic report JSON

---

## Authentification

### Session Cookie

**Extraction** : `getSessionFromCookie()` (depuis `@/lib/auth`)

**Format** : Session NextAuth avec `userEmail`

**Vérification** : `session && session.userEmail`

---

### JWT Signing

**Secret** : `process.env.JWT_SECRET_KEY || process.env.AUTH_SECRET || 'dev-secret-change-me'`

**Payload** :
```typescript
{
  sub: session.userEmail,
  email: session.userEmail
}
```

**Options** :
```typescript
{
  expiresIn: '1h'
}
```

**Header** : `Authorization: Bearer {token}`

---

### Backend URL

**Helper** : `buildBackendUrl(path)` (depuis `@/lib/backend`)

**Format** : `http://localhost:8000{path}` (dev) ou `process.env.BACKEND_URL{path}` (prod)

---

## Gestion d'erreurs UI

### Toast notifications

**Librairie** : `sonner`

**Usage** :
- `toast.success('Message')` : Succès
- `toast.error('Message')` : Erreur
- `toast.info('Message')` : Info

**Helpers** : `toastSuccess()`, `toastError()` (depuis `@/lib/admin/toast`)

---

### Affichage erreurs backend

**Format réponse erreur** :
```typescript
{
  error: 'Backend request failed',
  backend_status: 500,
  backend_body: {
    detail: 'Error message from backend'
  }
}
```

**Affichage** :
- Toast avec `error` ou `backend_body.detail`
- Console.error pour debug
- Affichage JSON dans UI (diagnostics)

---

## Types TypeScript

**Fichier** : `web/src/components/backtests/types.ts`

**Types principaux** :
- `InstrumentInfo`
- `BacktestCreateRequest`
- `BacktestRunResponse`
- `BacktestDetailResponse`
- `SeriesResponse`
- `PerformanceResponse`
- `PerformanceDataPoint`
- `PerformanceStats`
- `InstrumentPerformance`

**Alignement** : Types alignés avec Pydantic schemas backend.

---

## UI Components (Tailwind)

**Librairie** : `shadcn/ui` (composants Tailwind)

**Composants utilisés** :
- `Card`, `CardHeader`, `CardTitle`, `CardContent`
- `Button`
- `Input`
- `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`
- `Tabs`, `TabsContent`, `TabsList`, `TabsTrigger`
- `Progress`
- `ScrollArea`
- `Badge`

**Styling** : Tailwind CSS classes.

---

## Documents associés

- [Overview](./MARKET_DATA_AND_BACKTEST_OVERVIEW.md)
- [Market Data Architecture](./MARKET_DATA_ARCHITECTURE.md)
- [Backtest Engine Architecture](./BACKTEST_ENGINE_ARCHITECTURE.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






