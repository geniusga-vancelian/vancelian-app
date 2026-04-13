# Référence Architecture Backtests - Arquantix

Ce document fournit une référence complète sur l'architecture des backtests dans Arquantix.

---

## 1. Modèles SQLAlchemy

### 1.1 BacktestRun

**Fichier**: `api/database.py` (lignes 192-216)

```python
class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = ({"schema": "public"})
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    created_by_user_id = Column(Integer, nullable=True)  # No FK, quant DB isolated
    created_by_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    effective_start_date = Column(Date, nullable=True)
    effective_end_date = Column(Date, nullable=True)
    rebalance = Column(String(20), nullable=False)  # "daily", "weekly", "monthly"
    strategy_type = Column(String(50), nullable=False)  # "equal_weight", "momentum", "bundle_strategy", "CPPI", "CORE_SATELLITE"
    strategy_params_json = Column(JSON, nullable=True)  # Dict with strategy-specific params
    fees_bps = Column(Numeric(10, 4), nullable=False, server_default="0.0")
    slippage_bps = Column(Numeric(10, 4), nullable=False, server_default="0.0")
    allow_weekend_trading = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string
    instrument_ids_json = Column(JSON, nullable=False)  # Array of instrument IDs
    bundle_id = Column(String(36), nullable=True)  # Optional bundle ID (stored as string)
    status = Column(String(20), nullable=False, server_default="PENDING")  # "PENDING", "SUCCESS", "FAILED"
    error_message = Column(Text, nullable=True)
    
    # Relationships
    portfolio_series = relationship("BacktestPortfolioSeries", backref="run")
    instrument_series = relationship("BacktestInstrumentSeries", backref="run")
    metrics = relationship("BacktestMetrics", backref="run")
```

**Champs clés**:
- `strategy_type`: "equal_weight", "momentum", "bundle_strategy", "CPPI", "CORE_SATELLITE"
- `strategy_params_json`: JSON dict contenant les paramètres spécifiques à la stratégie
- `status`: "PENDING", "SUCCESS", "FAILED"
- `instrument_ids_json`: Liste d'entiers (IDs d'instruments)
- `bundle_id`: Optionnel, référence un bundle (stocké comme string)

---

### 1.2 BacktestPortfolioSeries

**Fichier**: `api/database.py` (lignes 219-235)

```python
class BacktestPortfolioSeries(Base):
    __tablename__ = "backtest_portfolio_series"
    __table_args__ = ({"schema": "public"})
    
    run_id = Column(Integer, ForeignKey("public.backtest_runs.id"), primary_key=True, nullable=False, index=True)
    date = Column(Date, primary_key=True, nullable=False, index=True)
    nav_base100 = Column(Numeric(20, 8), nullable=False)  # NAV base 100 (voir section 6)
    portfolio_return = Column(Numeric(20, 8), nullable=False)  # Return en pourcentage
    drawdown = Column(Numeric(20, 8), nullable=False)
    turnover = Column(Numeric(20, 8), nullable=False)
    costs = Column(Numeric(20, 8), nullable=False)
    weights_json = Column(JSON, nullable=True)  # Dict de instrument_id: weight + métadonnées stratégie
    tradable_json = Column(JSON, nullable=True)  # Dict de instrument_id: tradable (bool)
    
    run = relationship("BacktestRun", backref="portfolio_series")
```

**Structure `weights_json`** (varie selon la stratégie):

**Pour CPPI**:
```json
{
  "1": 0.5,  // instrument_id: weight (pour instrument 1)
  "2": 0.5,  // instrument_id: weight (pour instrument 2)
  "_cppi_risky_weight": 1.0,  // Poids total risqué (0-1)
  "_cppi_core_weight": 0.0,   // Poids core (0-1)
  "_cppi_floor": 90.0,        // Floor absolu (en unités de capital)
  "_cppi_cushion": 10.0       // Cushion absolu
}
```

**Pour CORE_SATELLITE**:
```json
{
  "1": 0.3,  // instrument_id: weight (satellite, après application du scalaire)
  "2": 0.2,  // instrument_id: weight
  "_core_weight": 0.5,              // Poids core (0-1)
  "_cs_alloc_mode": "te_target",    // Mode d'allocation V2.1
  "_cs_sat_weight_scalar": 0.5,     // Poids scalaire satellite (0-1)
  "_cs_te_sat": 0.12,               // TE annualisée du satellite
  "_cs_ir_sat": 0.85,               // Information Ratio du satellite
  "_te_realized": 0.10,             // TE réalisé (si calculé)
  "_te_pred": 0.11,                 // TE prédit
  // ... autres champs V2/V2.1
}
```

**Pour autres stratégies**:
```json
{
  "1": 0.5,  // instrument_id: weight
  "2": 0.5
}
```

---

### 1.3 BacktestMetrics

**Fichier**: `api/database.py` (lignes 254-268)

```python
class BacktestMetrics(Base):
    __tablename__ = "backtest_metrics"
    __table_args__ = ({"schema": "public"})
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("public.backtest_runs.id"), nullable=False, index=True)
    scope = Column(String(20), nullable=False)  # "portfolio" or "instrument"
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), nullable=True, index=True)
    key = Column(String(50), nullable=False)  # Metric name: "total_return", "sharpe_ratio", "volatility", etc.
    value = Column(Numeric(20, 8), nullable=False)
    
    run = relationship("BacktestRun", backref="metrics")
    instrument = relationship("MarketDataInstrument", backref="metrics")
```

**Métriques typiques** (`scope="portfolio"`):
- `total_return`: Return total (en décimal, ex: 0.1047 = 10.47%)
- `annualized_return`: Return annualisé (en décimal)
- `volatility`: Volatilité annualisée (en décimal)
- `sharpe_ratio`: Ratio de Sharpe
- `max_drawdown`: Drawdown maximum (en décimal, négatif)
- `realized_te`: Tracking Error réalisé (pour CORE_SATELLITE)
- `avg_core_weight`: Poids core moyen (pour CORE_SATELLITE)

**Métriques typiques** (`scope="instrument"`, `instrument_id` défini):
- `cagr`, `volatility`, `sharpe_ratio`, `max_drawdown`, etc. (mêmes que portfolio, mais pour l'instrument)

---

## 2. Exemple réel d'un backtest CPPI stocké

**Run ID**: 90  
**Strategy**: CPPI  
**Status**: SUCCESS

### 2.1 BacktestRun

```json
{
  "id": 90,
  "name": null,
  "strategy_type": "CPPI",
  "status": "SUCCESS",
  "start_date": "2020-03-12",
  "end_date": "2021-03-12",
  "effective_start_date": "2020-03-12",
  "effective_end_date": "2021-03-12",
  "rebalance": "weekly",
  "strategy_params_json": {
    "floor_ratio": 0.9,
    "multiplier": 4.0,
    "risky_cap": 1.0,
    "core_min": 0.0,
    "core_yield": 0.1,
    "day_count": 365,
    "debug": false
  },
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": "true",
  "instrument_ids_json": [1, 2],
  "bundle_id": null,
  "created_at": "2024-12-XX..."
}
```

### 2.2 BacktestPortfolioSeries (premier élément)

```json
{
  "run_id": 90,
  "date": "2020-03-12",
  "nav_base100": 100.0,
  "portfolio_return": 0.0,
  "drawdown": 0.0,
  "turnover": 0.0,
  "costs": 0.0,
  "weights_json": {
    "1": 0.0,  // instrument 1: 0% (tout en core au début)
    "2": 0.0,  // instrument 2: 0%
    "_cppi_risky_weight": 0.0,
    "_cppi_core_weight": 1.0,
    "_cppi_floor": 90.0,      // floor_ratio * initial_capital = 0.9 * 100
    "_cppi_cushion": 10.0     // initial_capital - floor = 100 - 90
  },
  "tradable_json": {
    "1": true,
    "2": true
  }
}
```

### 2.3 BacktestMetrics (portfolio)

```json
[
  {"scope": "portfolio", "key": "total_return", "value": 1.0468...},
  {"scope": "portfolio", "key": "annualized_return", "value": 0.1926...},
  {"scope": "portfolio", "key": "volatility", "value": 0.1728...},
  {"scope": "portfolio", "key": "sharpe_ratio", "value": 1.1145...},
  {"scope": "portfolio", "key": "max_drawdown", "value": -0.2178...}
]
```

---

## 3. Endpoints FastAPI liés aux backtests

**Fichier**: `api/services/backtest/routes.py`

**Router prefix**: `/api/backtests`

### 3.1 POST `/api/backtests/run`

**Description**: Créer et exécuter un nouveau backtest

**Request Body** (`BacktestRunRequest`):
```json
{
  "name": "Mon backtest CPPI",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "instrument_ids": [1, 2],
  "bundle_id": null,  // Optionnel
  "strategy": {
    "type": "CPPI",
    "params": {
      "floor_ratio": 0.9,
      "multiplier": 4.0,
      "core_yield": 0.035,
      "debug": false
    }
  },
  "rebalance": "weekly",
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": true
}
```

**Response** (`BacktestRunResponse`):
```json
{
  "run_id": 90,
  "id": 90,
  "name": "Mon backtest CPPI",
  "status": "SUCCESS",
  "created_at": "2024-12-XX...",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "message": "Backtest completed successfully."
}
```

**Codes de statut**:
- `201`: Backtest créé et exécuté avec succès
- `400`: Erreur de validation (dates invalides, instruments manquants, etc.)
- `422`: Erreur de validation de bundle (allocations invalides)
- `404`: Bundle non trouvé

---

### 3.2 GET `/api/backtests/{run_id}`

**Description**: Récupérer les détails d'un backtest par ID

**Response**:
```json
{
  "run": {
    "id": 90,
    "name": "Mon backtest CPPI",
    "status": "SUCCESS",
    "created_at": "2024-12-XX...",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "effective_start_date": "2024-01-01",
    "effective_end_date": "2024-12-31",
    "rebalance": "weekly",
    "strategy_type": "CPPI",
    "strategy_params_json": {...},
    "fees_bps": 0.0,
    "slippage_bps": 0.0,
    "allow_weekend_trading": true,
    "instrument_ids_json": [1, 2],
    "bundle_id": null,
    "error_message": null
  }
}
```

**Codes de statut**:
- `200`: Succès
- `404`: Backtest non trouvé

---

### 3.3 GET `/api/backtests/{run_id}/series`

**Description**: Récupérer les séries temporelles (portfolio + instruments)

**Response**:
```json
{
  "portfolio": [
    {
      "date": "2024-01-01",
      "nav_base100": 100.0,
      "portfolio_return": 0.0,
      "drawdown": 0.0,
      "turnover": 0.0,
      "costs": 0.0,
      "weights_json": {...},
      "tradable_json": {...}
    },
    ...
  ],
  "instruments": [
    {
      "instrument_id": 1,
      "symbol": "BTC",
      "series": [
        {
          "date": "2024-01-01",
          "base100": 100.0,
          "instrument_return": 0.0
        },
        ...
      ]
    },
    ...
  ]
}
```

**Codes de statut**:
- `200`: Succès
- `404`: Backtest non trouvé

---

## 4. Composants React pour les charts de backtests

**Répertoire**: `web/src/components/backtests/`

### 4.1 BacktestChart

**Fichier**: `web/src/components/backtests/BacktestChart.tsx`

**Description**: Graphique principal de performance (NAV portfolio + instruments + floor si CPPI)

**Props**:
```typescript
interface BacktestChartProps {
  portfolio: PortfolioBar[]
  instruments: InstrumentSeries[]
  layout?: 'single' | 'multiples'
  strategyType?: string  // 'CPPI' pour afficher Floor
  floorRatio?: number    // floor_ratio pour CPPI (default 0.9)
}
```

**Fonctionnalités**:
- Affiche NAV portfolio (base100)
- Affiche instruments individuels (base100)
- Si `strategyType === 'CPPI'`: affiche Floor (converti en base100)
- Layout `single`: un seul graphique
- Layout `multiples`: graphique portfolio + groupes d'instruments

---

### 4.2 CPPICharts

**Fichier**: `web/src/components/backtests/CPPICharts.tsx`

**Description**: Graphiques spécifiques CPPI (allocation Core vs Risky)

**Props**:
```typescript
interface CPPIChartsProps {
  portfolio: PortfolioBar[]
  strategyParams?: {
    floor_ratio?: number
    multiplier?: number
    risky_cap?: number
    core_min?: number
  }
}
```

**Graphiques**:
- **CPPI Allocation (Core vs Risky)**: Graphique pleine largeur (400px) montrant les poids Core et Risky en pourcentage

**Données utilisées**:
- `weights_json._cppi_risky_weight`
- `weights_json._cppi_core_weight`

---

### 4.3 CoreSatelliteCharts

**Fichier**: `web/src/components/backtests/CoreSatelliteCharts.tsx`

**Description**: Graphiques spécifiques CORE_SATELLITE (allocation Core vs Satellite, TE, cushion)

**Props**:
```typescript
interface CoreSatelliteChartsProps {
  portfolio: PortfolioBar[]
  strategyParams?: Record<string, any>
}
```

**Graphiques**:
- **Core-Satellite Allocation**: Graphique pleine largeur montrant Core Weight (%) et Satellite Weight (%)
- **Tracking Error (Realized vs Target)**: Si `_te_realized` présent
- **Dynamic Cushion**: Si `allocation_mode === "dynamic_cushion"` et `_cs_cushion` présent

**Données utilisées**:
- `weights_json._core_weight`
- `weights_json._cs_sat_weight_scalar`
- `weights_json._te_realized`
- `weights_json._cs_rel_index`, `_cs_rel_floor`, `_cs_cushion` (si dynamic_cushion)

---

### 4.4 BacktestStatsTable

**Fichier**: `web/src/components/backtests/BacktestStatsTable.tsx`

**Description**: Tableau de statistiques (métriques portfolio + instruments)

**Props**:
```typescript
interface BacktestStatsTableProps {
  portfolioMetrics: Record<string, number>
  instrumentMetrics: Array<{
    instrument_id: number
    symbol: string
    metrics: Record<string, number>
  }>
}
```

**Métriques affichées**:
- CAGR (%)
- Volatility (%)
- Sharpe Ratio
- Calmar Ratio
- Max Drawdown (%)
- Mean Daily Return (%)
- Variance Daily Return

---

### 4.5 Autres composants

- `BacktestResults.tsx`: Wrapper pour afficher résultats complets
- `BacktestBuilder.tsx`: Composant de construction de backtest (obsolète, remplacé par page admin)
- `HistoryChart.tsx`: Graphique d'historique (si utilisé)
- `HistoryStatsTable.tsx`: Tableau d'historique (si utilisé)

---

## 5. Page /admin/backtests

**Fichier**: `web/src/app/admin/backtests/page.tsx`

**Description**: Page principale d'administration des backtests (configuration + résultats)

**Layout**: Deux colonnes (grid lg:grid-cols-2)
- **Colonne gauche**: Configuration du backtest
- **Colonne droite**: Graphiques et résultats

### 5.1 Configuration (colonne gauche)

**Sections**:
1. **Nom du backtest** (optionnel)
2. **Source des instruments**: 
   - Instruments individuels (checkboxes)
   - Bundle (dropdown)
3. **Période**: Date début / Date fin
4. **Stratégie**: Dropdown (varie selon source)
   - Si `instruments`: equal_weight, momentum, CPPI, CORE_SATELLITE
   - Si `bundle`: bundle_strategy, CPPI, CORE_SATELLITE
5. **Paramètres stratégie** (si CPPI/CORE_SATELLITE):
   - Textarea JSON pour paramètres
   - Bouton "Use defaults"
   - Checkbox "Debug logs"
6. **Rebalance**: daily, weekly, monthly
7. **Coûts**: Fees (bps), Slippage (bps)
8. **Weekend trading**: Checkbox
9. **Bouton "Lancer le Backtest"**

### 5.2 Résultats (colonne droite)

**Composants affichés**:
1. **Card Backtest Info**: Période, stratégie, rebalance, status
2. **Card Graphique de Performance**: `<BacktestChart />`
3. **Card CPPI Analytics** (si `strategy_type === 'CPPI'`): `<CPPICharts />`
4. **Card Core-Satellite Analytics** (si `strategy_type === 'CORE_SATELLITE'`): `<CoreSatelliteCharts />`
5. **Card Statistiques**: `<BacktestStatsTable />`

**Flow**:
1. Utilisateur configure et clique "Lancer le Backtest"
2. POST `/api/backtests/run` → reçoit `run_id`
3. `loadResults(run_id)` appelé:
   - GET `/api/backtests/{run_id}` → `backtestDetail`
   - GET `/api/backtests/{run_id}/series` → `backtestSeries`
4. Composants rendus avec les données

---

## 6. Convention NAV (base100)

### 6.1 Définition

**NAV base100** = `(NAV_actuel / NAV_initial) * 100`

Où:
- `NAV_initial` = capital initial (`initial_capital`)
- `NAV_actuel` = valeur nette du portefeuille à la date donnée

### 6.2 Implémentation

**Dans CPPI** (`api/services/backtest/strategies/cppi.py`, ligne 237):
```python
nav_base100 = (V_t / V0 * 100.0) if V0 > 0 else 100.0
```

Où:
- `V0` = capital initial (`initial_capital`)
- `V_t` = valeur totale à la date t

**Dans CORE_SATELLITE** (`api/services/backtest/strategies/core_satellite.py`, ligne 308):
```python
nav_base100 = (portfolio_nav / initial_capital) * 100.0
```

### 6.3 Propriétés

- **Date initiale**: `nav_base100 = 100.0` (toujours)
- **Valeur relative**: `nav_base100 = 150.0` signifie +50% vs capital initial
- **Stockage**: Colonne `nav_base100` de type `Numeric(20, 8)` (décimal)

### 6.4 Instruments (base100)

**Pour les instruments individuels**:
```python
base100 = (price / first_price * 100.0) if first_price > 0 else 100.0
```

Où:
- `first_price` = prix à la date de début du backtest
- `price` = prix à la date donnée

**Stockage**: Colonne `base100` dans `backtest_instrument_series`

### 6.5 Floor CPPI (base100)

**Floor absolu** (stocké dans `weights_json._cppi_floor`):
- Valeur absolue en unités de capital
- Exemple: Floor = 90.0 si `floor_ratio=0.9` et `initial_capital=100`

**Floor base100** (pour affichage dans chart):
- Conversion: `floor_base100 = (floor_absolute / initial_capital) * 100`
- Alternative (avec `floor_ratio`): `floor_base100 = floor_ratio * 100`
- Exemple: Floor base100 = 90.0 si `floor_ratio=0.9`

**Code de conversion** (`BacktestChart.tsx`, lignes 45-54):
```typescript
// floor_base100 = (floor_ratio * 100) / first_floor_absolute * floor_absolute
floorConversionFactor = (floorRatio * 100) / firstFloor
floor_base100 = floorValue * floorConversionFactor
```

Cela garantit que le floor commence à `floor_ratio * 100` (ex: 90 si `floor_ratio=0.9`).

---

## 7. Résumé des conventions

### 7.1 Types de stratégies

- `equal_weight`: Allocation égale entre instruments
- `momentum`: Allocation basée sur momentum
- `bundle_strategy`: Allocation fixe du bundle
- `CPPI`: Constant Proportion Portfolio Insurance
- `CORE_SATELLITE`: Core-Satellite (V1/V2/V2.1)

### 7.2 Format de dates

- **API**: Format ISO `YYYY-MM-DD` (string)
- **Base de données**: Type `Date` (PostgreSQL)
- **Frontend**: Format ISO ou `Date` object JavaScript

### 7.3 Format des poids

- **Stockage**: Décimal 0.0-1.0 (ex: 0.5 = 50%)
- **Affichage**: Pourcentage 0-100% (ex: 50%)
- **Conversion**: `pourcentage = decimal * 100`

### 7.4 Format des returns

- **Stockage**: Décimal (ex: 0.05 = 5%)
- **Affichage**: Pourcentage (ex: 5%)
- **Conversion**: `pourcentage = decimal * 100`

### 7.5 JSON fields

- `weights_json`: Dict avec clés string (instrument IDs) + métadonnées stratégie
- `tradable_json`: Dict avec clés string (instrument IDs) + valeurs bool
- `strategy_params_json`: Dict avec paramètres stratégie (structure varie)

---

## 8. Fichiers clés

### Backend

- `api/database.py`: Modèles SQLAlchemy
- `api/services/backtest/routes.py`: Endpoints FastAPI
- `api/services/backtest/executor.py`: Logique d'exécution
- `api/services/backtest/strategies/cppi.py`: Implémentation CPPI
- `api/services/backtest/strategies/core_satellite.py`: Implémentation Core-Satellite

### Frontend

- `web/src/app/admin/backtests/page.tsx`: Page principale
- `web/src/components/backtests/BacktestChart.tsx`: Graphique principal
- `web/src/components/backtests/CPPICharts.tsx`: Charts CPPI
- `web/src/components/backtests/CoreSatelliteCharts.tsx`: Charts Core-Satellite
- `web/src/components/backtests/BacktestStatsTable.tsx`: Tableau statistiques
- `web/src/components/backtests/types.ts`: Types TypeScript
- `web/src/app/api/backtests/run/route.ts`: Proxy Next.js → FastAPI

---

**Dernière mise à jour**: 2024-12-XX
