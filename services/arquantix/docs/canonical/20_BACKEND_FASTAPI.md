# Backend FastAPI — Structure & Routes

**Fichiers clés**: `api/main.py`, `api/services/*`, `api/database.py`, `api/auth.py`

---

## 1. Organisation par domaine

### Structure (`api/services/`)

```
services/
├── market_data/
│   ├── routes.py              # GET/POST/PUT/DELETE instruments, GET bars
│   ├── yahoo_client.py        # Client Yahoo Finance (yfinance)
│   ├── config.py              # Configuration (MARKET_DATA_PROVIDER, etc.)
│   ├── schemas.py             # Schémas Pydantic (si existe)
│   └── client.py              # DEPRECATED (Alpha Vantage)
├── bundles/
│   └── routes.py              # CRUD bundles, allocations
├── backtest/
│   ├── routes.py              # POST /run, GET /{id}, GET /{id}/series
│   ├── executor.py            # Exécution backtest (weights, NAV, metrics)
│   ├── repository.py          # DB operations (load_instruments, load_open_bars, store_*)
│   └── schemas.py             # Schémas Pydantic (si existe)
├── diagnostics/
│   ├── routes.py              # Endpoints diagnostics (market data, backtest)
│   └── market_backtest.py     # Fonctions diagnostics
└── ai_email/                  # UNKNOWN (non vérifié dans ce contexte)
```

**Référence**: `api/main.py:64-68` - Inclusion des routers

---

## 2. Application FastAPI (`api/main.py`)

### Configuration

**CORS**:
```python
allow_origins=["http://localhost:3001", "http://localhost:3000", "http://localhost:3011"]
allow_credentials=True
```

**Référence**: `api/main.py:46-53`

### Routers inclus

```python
app.include_router(bundles_router)           # /api/bundles
app.include_router(diagnostics_router)       # /api/diagnostics
app.include_router(market_data_router)       # /api/market-data
app.include_router(backtest_router)          # /api/backtests
```

**Référence**: `api/main.py:64-68`

### Endpoints publics

- `GET /` - Root (healthcheck)
- `GET /health` - Healthcheck
- `POST /auth/login` - Login (retourne JWT)
- `GET /public/*` - Endpoints publics (site vitrine)

**Référence**: `api/main.py:75-191`

### Endpoints admin (protégés JWT)

- `GET /admin/*` - Endpoints admin (nécessitent `Depends(get_current_user)`)
- `POST /admin/uploads` - Upload fichiers
- `POST /admin/pages/{id}/translate` - Traduction pages

**Référence**: `api/main.py:195-633`

---

## 3. Routes principales (par module)

### Market Data (`api/services/market_data/routes.py`)

**Router**: `APIRouter(prefix="/api/market-data", tags=["market-data"])`

**Routes**:
- `GET /instruments` - Liste instruments (filtre `is_active`)
- `POST /instruments` - Créer instrument
- `PUT /instruments/{id}` - Mettre à jour instrument
- `DELETE /instruments/{id}` - Supprimer instrument
- `GET /instruments/{id}/bars` - Récupérer bars historiques (filtres `start`, `end`)

**Référence**: `api/services/market_data/routes.py:72-292`

### Bundles (`api/services/bundles/routes.py`)

**Router**: `APIRouter(prefix="/api/bundles", tags=["bundles"])`

**Routes**:
- `GET ""` - Liste bundles (filtrés par `is_active == "true"`)
- `GET /{bundle_id}` - Détails bundle
- `POST ""` - Créer bundle (avec allocations)
- `PUT /{bundle_id}` - Mettre à jour bundle
- `DELETE /{bundle_id}` - Supprimer bundle

**Référence**: `api/services/bundles/routes.py:51-411`

### Backtests (`api/services/backtest/routes.py`)

**Router**: `APIRouter(prefix="/api/backtests", tags=["backtests"])`

**Routes**:
- `POST /run` - Créer et exécuter backtest
- `GET /{run_id}` - Détails backtest run
- `GET /{run_id}/series` - Séries portfolio et instruments

**Référence**: `api/services/backtest/routes.py:56-312`

### Diagnostics (`api/services/diagnostics/routes.py`)

**Router**: `APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])`

**Routes**:
- `GET /market-backtest` - Diagnostic market data + backtest
- `POST /jwt-debug` - Debug JWT (DEV-ONLY)

**Référence**: `api/services/diagnostics/routes.py`

---

## 4. Schémas Pydantic importants

### Market Data

**InstrumentCreate** (`api/services/market_data/routes.py:34-41`):
```python
class InstrumentCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    asset_class: str  # "crypto", "etf", "equity", "forex", "index", "commodities"
    weekend_tradable: bool = False
    provider: str = "yahoo"
    provider_symbol: Optional[str] = None
    is_active: bool = True
```

**InstrumentResponse** (`api/services/market_data/routes.py:53-65`):
- `id`, `symbol`, `name`, `asset_class`, `weekend_tradable` (string), `provider`, `provider_symbol`, `is_active` (string), `created_at`

**Note**: `weekend_tradable` et `is_active` sont stockés comme strings (`"true"`/`"false"`) dans la DB.

### Bundles

**BundleCreate** (`api/services/bundles/routes.py:21-25`):
```python
class BundleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instrument_ids: List[int]
    allocations: Optional[dict] = None  # Map of instrument_id: allocation_percentage
```

**BundleResponse** (`api/services/bundles/routes.py:34-44`):
- `id` (string), `name`, `description`, `instrument_ids`, `instruments` (optional list), `created_at`, `updated_at`

**Validation allocations**:
- Total allocation doit être 100% (tolérance 0.01%)
- Tous les `instrument_ids` doivent avoir une allocation

**Référence**: `api/services/bundles/routes.py:222-237`

### Backtests

**BacktestRunRequest** (`api/services/backtest/routes.py:29-39`):
```python
class BacktestRunRequest(BaseModel):
    name: Optional[str] = None
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    instrument_ids: Optional[List[int]] = None
    bundle_id: Optional[str] = None
    strategy: BacktestStrategy
    rebalance: str  # "daily", "weekly", "monthly"
    fees_bps: float
    slippage_bps: float
    allow_weekend_trading: bool
```

**BacktestStrategy** (`api/services/backtest/routes.py:24-26`):
```python
class BacktestStrategy(BaseModel):
    type: str  # "equal_weight", "momentum", or "bundle_strategy"
    params: Optional[BacktestStrategyParams] = None
```

**Référence**: `api/services/backtest/routes.py:20-49`

---

## 5. Validation (422, XOR, model_validator)

### Validation Pydantic standard

**Erreurs 422**: Validation automatique FastAPI sur schémas Pydantic.

**Exemple**: Si `start_date` n'est pas `YYYY-MM-DD`, FastAPI retourne 422.

**Référence**: `api/services/backtest/routes.py:64-68`

### Validation XOR (instruments vs bundle)

**Contrainte**: `instrument_ids` OU `bundle_id` (pas les deux, pas aucun).

**Implémentation**:
```python
if request.bundle_id:
    # Load from bundle
    instrument_ids = [comp.instrument_id for comp in components]
else:
    instrument_ids = request.instrument_ids

if not instrument_ids or len(instrument_ids) == 0:
    raise HTTPException(status_code=400, detail="instrument_ids or bundle_id must be provided")
```

**Référence**: `api/services/backtest/routes.py:73-98`

### Validation allocations bundle

**Contrainte**: Total allocations = 100% (tolérance 0.01%).

**Implémentation**:
```python
if allocations_normalized:
    total_allocation = sum(float(v) for v in allocations_normalized.values() if v is not None)
    if abs(total_allocation - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Total allocation must be 100%. Current total: {total_allocation:.2f}%")
```

**Référence**: `api/services/bundles/routes.py:223-229`

### Validation type bundle (CHECK constraint)

**Contrainte DB**: `type` doit être `'fixed_instruments'`, `'composite_fixed'`, ou `'dynamic'`.

**Vérification**: Contrainte CHECK `chk_bundles_type_valid` dans PostgreSQL.

**Référence**: Migration (non trouvée dans code, vérifiée via DB: `chk_bundles_type_valid`)

---

## 6. Erreurs connues et fixes

### Erreur 500: `asset_class` NOT NULL violation

**Problème**: `bundles.asset_class` est NOT NULL dans la DB mais non défini lors de la création.

**Fix**: Calcul de `asset_class` à partir des instruments sélectionnés (classe la plus commune, ou "mixed" si aucun).

**Référence**: `api/services/bundles/routes.py:180-189`

### Erreur 500: `type` CHECK violation

**Problème**: Valeur `type="FIXED_WEIGHT"` ne respecte pas la contrainte CHECK (`'fixed_instruments'`, `'composite_fixed'`, `'dynamic'`).

**Fix**: Utilisation de `type="fixed_instruments"` pour les bundles avec allocations fixes.

**Référence**: `api/services/bundles/routes.py:194-198`

### Erreur 500: `NaN` dans JSON PostgreSQL

**Problème**: `weights_json` contient `NaN` (incompatible avec JSON PostgreSQL).

**Fix**: Conversion `NaN` et `inf` en `None` (devient `null` en JSON) avant stockage.

**Référence**: `api/services/backtest/executor.py:191-196`, `api/services/backtest/repository.py:107-124`

### Erreur 422: `allocations` manquant dans schéma Zod

**Problème**: Frontend supprime `allocations` car non présent dans `createBundleSchema`.

**Fix**: Ajout de `allocations: z.record(z.string(), z.number()).optional().nullable()` dans le schéma Zod.

**Référence**: `web/src/app/api/bundles/route.ts:11`

---

## 7. Gestion d'erreurs (400/409/422)

### Codes HTTP utilisés

- **200 OK**: Succès GET
- **201 Created**: Succès POST (création)
- **204 No Content**: Succès DELETE
- **400 Bad Request**: Validation métier (allocations != 100%, instrument_ids manquant, etc.)
- **401 Unauthorized**: JWT invalide ou manquant
- **404 Not Found**: Ressource introuvable (bundle, instrument, backtest run)
- **409 Conflict**: UNKNOWN (non vérifié)
- **422 Unprocessable Entity**: Validation Pydantic (format date invalide, etc.)
- **500 Internal Server Error**: Erreur serveur (exception non gérée)
- **502 Bad Gateway**: Backend indisponible (côté Next.js proxy)

### Conventions

**Erreurs 400**:
- Message détaillé: `detail="Total allocation must be 100%. Current total: 80.00%"`
- Raison claire: `detail=f"Some instrument IDs not found: {list(missing_ids)}"`

**Erreurs 404**:
- Message simple: `detail="Bundle not found"`

**Erreurs 422**:
- Auto-générées par FastAPI (format: `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`)

**Référence**: `api/services/bundles/routes.py`, `api/services/backtest/routes.py`

---

## 8. Healthcheck

**Endpoint**: `GET /health`

**Réponse**:
```json
{"status": "ok", "service": "arquantix-api"}
```

**Référence**: `api/main.py:80-82`

**Usage**: Vérification que l'API est accessible (`curl http://localhost:8000/health`).

---

## 9. Authentification JWT

**Endpoint**: `POST /auth/login`

**Request**:
```json
{
  "email": "admin@local.dev",
  "password": "password"
}
```

**Response**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Utilisation**: Header `Authorization: Bearer <token>` sur endpoints admin.

**Référence**: `api/auth.py`, `api/main.py:89-104`

### JWT Secret Key

**Source**: Variable d'environnement `JWT_SECRET_KEY` (fallback: `"your-secret-key-change-in-production"`).

**Référence**: `api/auth.py:24-35`

### Expiration

**Durée**: `ACCESS_TOKEN_EXPIRE_MINUTES` (valeur: UNKNOWN, vérifier `api/auth.py`).

**Référence**: `api/auth.py:100`

---

## 10. Configuration

### Variables d'environnement

**Fichiers**: `.env.local` (priorité) > `.env`

**Variables clés**:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret pour JWT
- `CORS_ORIGINS` - Origines autorisées (défaut: `"http://localhost:3001,http://localhost:3000,http://localhost:3011"`)
- `PORT` - Port FastAPI (défaut: `8000`)

**Référence**: `api/database.py:8-11`, `api/main.py:49`, `api/auth.py:24`

### Chargement .env

**Ordre**: `.env.local` chargé en premier, puis `.env` (écrasé).

**Référence**: `api/database.py:8-11`

---

## 11. Limitations actuelles

- **Backtest asynchrone**: TODO dans `api/services/backtest/routes.py:151` ("In production, this should be queued as an async task")
- **Bundle resolver**: UNKNOWN si implémenté (composite bundles, cycles)
- **Bundles dynamiques**: Type `dynamic` existe, mais UNKNOWN si les règles sont implémentées


