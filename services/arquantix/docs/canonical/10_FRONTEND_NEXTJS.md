# Frontend Next.js — Structure & Pages Admin

**Fichiers clés**: `web/src/app/admin/*`, `web/src/components/finance/*`, `web/src/app/api/*`

---

## 1. Structure des dossiers

### Pages Admin (`web/src/app/admin/`)

```
admin/
├── layout.tsx                    # Layout avec AdminSidebar
├── login/page.tsx               # Page de login
├── page.tsx                     # Dashboard principal
├── finance/page.tsx             # Page Finance (tabs: Market Data/Bundles/Backtests)
├── market-data/
│   ├── page.tsx                 # Page Instruments (DEPRECATED, voir finance)
│   └── upload/page.tsx          # Page Upload Data (création instruments)
├── bundles/page.tsx             # Page Bundles (DEPRECATED, voir finance)
├── backtests/page.tsx           # Page Backtests (DEPRECATED, voir finance)
└── [autres pages admin...]
```

**Important**: Les pages `/admin/market-data`, `/admin/bundles`, `/admin/backtests` existent encore mais sont **dépréciées**. Le contenu a été déplacé vers `/admin/finance` avec des onglets.

### Composants Finance (`web/src/components/finance/`)

- `MarketDataTab.tsx` - Onglet Market Data (table instruments + chart)
- `BundlesTab.tsx` - Onglet Bundles (liste + création modal)
- `BacktestsTab.tsx` - Onglet Backtests (config + résultats)

**Référence**: `web/src/app/admin/finance/page.tsx` utilise ces composants.

---

## 2. Page Finance (`/admin/finance`)

**Fichier**: `web/src/app/admin/finance/page.tsx`

### Structure

- **Header**: Titre "Finance" + bouton "← Back to Dashboard"
- **Tabs horizontaux**: Market Data | Bundles | Backtests
- **Contenu**: Composant correspondant au tab actif

### Navigation entre tabs

```typescript
const [activeTab, setActiveTab] = useState<'market-data' | 'bundles' | 'backtests'>('market-data')
```

**Design**: Tabs personnalisés (pas shadcn/ui Tabs), style similaire à `/admin/pages`.

---

## 3. Page Market Data (`/admin/market-data`)

**Fichier**: `web/src/app/admin/market-data/page.tsx` (déprécié)  
**Composant actif**: `web/src/components/finance/MarketDataTab.tsx`

### Layout (2 colonnes)

**Colonne gauche**:
- Table des instruments actifs
- Sélection unique (un instrument à la fois)
- Filtres:
  - **Affichage**: Base 100 | Prix Réel
  - **Type de graphique**: Line Chart | Candlestick
  - **Dates**: Date de début / Date de fin (défaut: 5 ans)

**Colonne droite**:
- Composant `InstrumentChart` (`web/src/components/market-data/InstrumentChart.tsx`)
- Graphique dynamique selon les filtres

### Bouton "Upload Data"

Redirige vers `/admin/market-data/upload` (formulaire création instrument + upload Yahoo HTML).

---

## 4. Page Upload Data (`/admin/market-data/upload`)

**Fichier**: `web/src/app/admin/market-data/upload/page.tsx`

### Contenu

- **Formulaire création instrument**:
  - Symbol (required)
  - Name
  - Asset Class (select: crypto, etf, equity, forex, index, commodities)
  - Provider Symbol (optionnel, défaut: symbol)
  - Weekend Tradable (checkbox)
  - Is Active (checkbox)
  - Bouton "Save"

- **Zone upload Yahoo Finance**:
  - Textarea pour copier-coller HTML de Yahoo Finance
  - Bouton "Save" pour parser et insérer les données

**Note**: UNKNOWN si le parsing HTML Yahoo Finance est implémenté dans le backend (non vérifié dans le code).

---

## 5. Proxy API Next.js (`web/src/app/api/`)

### Pourquoi il existe

Le frontend Next.js fait office de **proxy** entre le client et le backend FastAPI pour :

1. **Gestion de l'authentification**: Conversion session cookie Next.js → JWT FastAPI
2. **Validation Zod**: Validation côté frontend avant envoi au backend
3. **Gestion d'erreurs**: Transformation erreurs FastAPI → format frontend
4. **CORS**: Éviter les problèmes CORS (frontend et backend sur ports différents)

**Référence**: `web/src/app/api/bundles/route.ts` (exemple complet)

### Comment il fonctionne

**Schéma Zod** (`web/src/app/api/bundles/route.ts:7-12`):
```typescript
const createBundleSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().max(1000).optional().nullable(),
  instrument_ids: z.array(z.number()).min(1),
  allocations: z.record(z.string(), z.number()).optional().nullable(),
})
```

**Flux POST**:
1. Vérification session (`getSessionFromCookie()`)
2. Validation Zod (`createBundleSchema.parse(body)`)
3. Génération JWT (`jwt.sign({ sub: session.userEmail }, ...)`)
4. Proxy vers FastAPI (`fetch(backendUrl, { Authorization: Bearer ${token} })`)
5. Transformation erreurs si `!response.ok`

**Erreurs gérées**:
- `401 Unauthorized` - Pas de session
- `400 Bad Request` - Validation Zod échouée
- `502 Bad Gateway` - Backend indisponible (`ECONNREFUSED`, `ETIMEDOUT`)

### Erreurs rencontrées et corrections

**Problème**: Le champ `allocations` n'était pas dans le schéma Zod, donc supprimé avant envoi au backend.

**Correction**: Ajout de `allocations: z.record(z.string(), z.number()).optional().nullable()` dans `createBundleSchema`.

**Fichier**: `web/src/app/api/bundles/route.ts:11`

---

## 6. Composant InstrumentChart

**Fichier**: `web/src/components/market-data/InstrumentChart.tsx`

### Fonctionnalités

- **2 types de graphiques**:
  - **Line Chart** (`recharts`): `LineChart`, `XAxis`, `YAxis`, `Tooltip`, `Line`
  - **Candlestick** (`lightweight-charts` v5.1.0): `chart.addSeries(CandlestickSeries, ...)`

**Important**: `lightweight-charts` v5.1.0 utilise `chart.addSeries(CandlestickSeries, options)` et non `chart.addCandlestickSeries()`.

### Modes d'affichage

- **Base 100**: Normalisation du prix (première valeur = 100)
- **Prix Réel**: Prix brut de l'actif

### Données

**Endpoint**: `GET /api/market-data/instruments/{instrument_id}/bars?start=YYYY-MM-DD&end=YYYY-MM-DD`

**Format réponse**:
```json
{
  "instrument_id": 1,
  "symbol": "BTCUSD",
  "bars": [
    {
      "date": "2021-01-01",
      "open": 29374.15,
      "high": 29600.00,
      "low": 29000.00,
      "close": 29400.00,
      "volume": 123456789
    }
  ],
  "count": 1825,
  "start_date": "2021-01-01",
  "end_date": "2026-01-10"
}
```

### Corrections appliquées

**Problème**: Erreur `chart.addCandlestickSeries is not a function`.

**Cause**: API `lightweight-charts` v5.1.0 a changé.

**Correction**: Utilisation de `chart.addSeries(CandlestickSeries, {...})`.

**Problème**: Données OHLC invalides (high < low, open/close hors range).

**Correction**: Validation et correction des données:
- `high >= low` (swap si nécessaire)
- `open`, `close` dans `[low, high]` (clamp)

**Fichier**: `web/src/components/market-data/InstrumentChart.tsx`

---

## 7. États complexes (loading / error / empty)

### MarketDataTab

- **Loading**: `loadingInstruments` → Message "Chargement..."
- **Error**: `toastError()` via `@/lib/admin/toast`
- **Empty**: Pas d'instrument sélectionné → Pas de chart

### BundlesTab

- **Loading**: `loading` → Message "Chargement..."
- **Creating**: `creating` → Bouton "Créer Bundle" désactivé
- **Deleting**: `deleting` → Confirmation dialog
- **Empty**: `bundles.length === 0` → Message "Aucun bundle"

### BacktestsTab

- **Running**: `running` → Bouton "Lancer Backtest" désactivé
- **Loading Results**: `loadingResults` → Message "Chargement des résultats..."
- **Empty Series**: `backtestSeries === null || backtestSeries.portfolio.length === 0` → Pas de graphique

**Gestion d'erreurs**: Try/catch avec `toastError()` pour toutes les opérations async.

---

## 8. AdminSidebar

**Fichier**: `web/src/components/admin/AdminSidebar.tsx`  
**Intégration**: `web/src/app/admin/layout.tsx`

### Menu

- Dashboard
- Finance (nouveau, remplace Market Data/Bundles/Backtests individuellement)
- Market Data (conservé pour compatibilité)
- Bundles (conservé pour compatibilité)
- Backtests (conservé pour compatibilité)
- [autres liens...]

**Condition**: Sidebar masquée sur `/admin/login`.

---

## 9. Problèmes connus et fixes

### Front cassé après refactor

**Problème**: Erreur "The default export is not a React Component" sur `/admin/login`.

**Cause**: 
1. `useSearchParams()` nécessite `Suspense` en Next.js 13+
2. Layout admin vide (`web/src/app/admin/layout.tsx` retournait `<>`)

**Fix**:
- Wrapper `LoginForm` dans `<Suspense>`
- Layout admin retourne `<div>{children}</div>`
- Cache Next.js vidé: `rm -rf .next/cache`

**Fichiers**: `web/src/app/admin/login/page.tsx`, `web/src/app/admin/layout.tsx`

### Dropdowns transparents

**Problème**: Background transparent dans `Select` et `DropdownMenu`.

**Fix**: Modification de `web/src/components/ui/select.tsx` et `web/src/components/ui/dropdown-menu.tsx`:
- `bg-popover` → `bg-white`
- `focus:bg-accent` → `focus:bg-gray-100`

---

## 10. Limitations actuelles

- **Bundle de bundles (composite)**: Supporté dans la DB (`bundle_components.component_type = 'bundle'`), mais UNKNOWN si le resolver est implémenté
- **Bundles dynamiques**: Type `dynamic` existe, mais UNKNOWN si les règles sont implémentées
- **Parsing HTML Yahoo Finance**: UNKNOWN si implémenté dans le backend


