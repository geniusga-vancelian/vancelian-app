# ARCHITECTURE CANONIQUE ARQUANTIX

**Version**: 2026-01-10  
**Source**: Documentation basée uniquement sur le code existant (`api/`, `web/`, `scripts/`)  
**Statut**: Source de vérité pour reprise du projet à froid

---

## ⚠️ RÈGLES D'OR

Cette documentation est **CANONIQUE** :
- ✅ Basée uniquement sur le code existant
- ✅ Tous les chemins de fichiers sont vérifiés
- ✅ Toutes les structures de données sont traçables
- ❌ Aucune hypothèse non vérifiable
- ❌ Aucune invention

Si une information est marquée **UNKNOWN (needs confirmation)**, elle doit être vérifiée avant utilisation.

---

## 📚 TABLE DES MATIÈRES

### [00. Vue d'ensemble](canonical/00_OVERVIEW.md)
- Vision & objectifs
- Architecture globale (schéma ASCII)
- Flux de données
- Glossaire
- Structure des répertoires

### [10. Frontend Next.js](canonical/10_FRONTEND_NEXTJS.md)
- Structure `/admin` et `/components`
- Pages admin (market-data, bundles, backtests, finance)
- Proxy API Next.js (pourquoi, comment, erreurs & fixes)
- Composant InstrumentChart (line vs candlestick)
- États complexes (loading/error/empty)
- Problèmes connus et fixes

### [20. Backend FastAPI](canonical/20_BACKEND_FASTAPI.md)
- Organisation par domaine (`services/`)
- Routes principales (market_data, bundles, backtests, diagnostics)
- Schémas Pydantic importants
- Validation (422, XOR, model_validator)
- Gestion d'erreurs (400/404/422/500)
- Healthcheck & authentification JWT

### [30. Market Data](canonical/30_MARKET_DATA.md)
- Asset classes (crypto, etf, equity, forex, index, commodities)
- Instruments (symbol vs provider_symbol, normalisation)
- Table `market_data_bars_d1` (source de vérité)
- Provider Yahoo Finance (yfinance)
- Ingestion Yahoo HTML (UNKNOWN si implémenté)
- Smart update (dry_run, delta, overwrite)
- Repository `load_open_bars()`

### [40. Bundles](canonical/40_BUNDLES.md)
- Concept (bundle = stratégie figée)
- Types: `fixed_instruments`, `composite_fixed`, `dynamic`
- Tables: `bundles`, `bundle_components`, `bundle_allocations` (orphane), `bundle_dynamic_rules`
- Contraintes XOR (instrument vs bundle enfant)
- Resolver (UNKNOWN si implémenté)
- Preview API (UNKNOWN si implémenté)
- Création workflow
- Utilisation dans backtests

### [50. Backtests](canonical/50_BACKTESTS.md)
- Entrées XOR (`instrument_ids` vs `bundle_id`)
- Stratégies: `equal_weight`, `momentum`, `bundle_strategy`
- Rebalancing (daily/weekly/monthly)
- Skip rebalance si prix manquant (UNKNOWN)
- Drift, turnover, coûts (fees_bps, slippage_bps)
- Calcul performances (NAV, drawdown, metrics)
- Endpoints `/api/backtests`
- Exécution workflow
- Gestion NaN (conversion avant stockage)

### [60. Base de données & Migrations](canonical/60_DATABASE_ALEMBIC.md)
- Tables clés (liste exhaustive vérifiée)
- Relations (FK, schéma ASCII)
- Contraintes importantes (CHECK, UNIQUE, PK)
- Migrations Alembic critiques (ordre, objectifs)
- Seeds / Fixtures (`seed.py`, `load_market_data.py`)
- Schéma DB (arquantix_quant, public)
- Inconsistances modèle SQLAlchemy vs DB réelle

### [70. Runbook Développement](canonical/70_RUNBOOK_DEV.md)
- Démarrage local (`arquantix-start.sh`)
- Ports (3000, 8000, 5443)
- Variables d'environnement (`.env.local`, `.env`)
- Debug (logs, erreurs 500/422/409/502)
- Checklist "après reboot"
- Commandes utiles (status, arrêt, cache, migrations)
- Scripts utilitaires (`load_market_data.py`, `seed.py`)

---

## 🔒 INVARIANTS DU PROJET

**Ce qui ne doit JAMAIS être cassé** :

1. **`market_data_bars_d1` est la source unique de vérité**
   - Tous les modules (charts, backtests) doivent utiliser `load_open_bars()` depuis cette table
   - Pas de fetch direct Yahoo Finance dans les modules

2. **Bundles = allocations figées (100% obligatoire)**
   - Total allocations doit être exactement 100% (tolérance 0.01%)
   - Backtest avec bundle → stratégie fixée à `"bundle_strategy"` automatiquement

3. **Backtest XOR: `instrument_ids` OU `bundle_id`**
   - Pas les deux, pas aucun
   - Validation explicite dans `api/services/backtest/routes.py:113-114`

4. **Gestion NaN avant stockage JSON PostgreSQL**
   - Conversion `NaN` / `inf` → `None` (devient `null` en JSON)
   - Applicable à: `weights_json`, `nav_base100`, `portfolio_return`, etc.

5. **Contraintes DB CHECK doivent être respectées**
   - `bundles.type` IN (`'fixed_instruments'`, `'composite_fixed'`, `'dynamic'`)
   - `bundle_components` XOR (instrument OU bundle enfant)
   - `weight >= 0`

6. **Provider Yahoo Finance uniquement**
   - Alpha Vantage déprécié (code restant dans `client.py` mais non utilisé)
   - Default provider: `"yahoo"`

---

## 🚨 RÈGLES D'OR

1. **Ne jamais inventer**: Si une fonctionnalité n'est pas vérifiée dans le code → marquer **UNKNOWN (needs confirmation)**

2. **Toujours vérifier la DB réelle**: Les modèles SQLAlchemy peuvent être inconsistants avec la DB (ex: `asset_class` nullable dans modèle mais NOT NULL en DB)

3. **Contraintes CHECK**: Toujours vérifier via `pg_get_constraintdef()` dans PostgreSQL

4. **Migrations orphelines**: Certaines migrations peuvent créer des tables non utilisées (ex: `market_data_bundles` dans `a39b971e0c8c`)

5. **Forward fill pour prix manquants**: `load_open_bars()` forward fill les prix manquants (pas de skip rebalance explicite)

6. **Conversion NaN**: Toujours convertir `NaN` / `inf` → `None` avant stockage JSON dans PostgreSQL

---

## 🔄 COMMENT REPRENDRE LE PROJET APRÈS UN ARRÊT

### 1. Fichiers à lire en priorité

**Architecture globale**:
- `docs/canonical/00_OVERVIEW.md` - Vue d'ensemble
- `docs/canonical/70_RUNBOOK_DEV.md` - Démarrage

**Code clé**:
- `api/database.py` - Modèles SQLAlchemy (structure DB)
- `api/main.py` - FastAPI app (routers inclus)
- `web/src/app/admin/finance/page.tsx` - Page Finance principale

**Scripts**:
- `scripts/arquantix-start.sh` - Démarrage automatique
- `api/scripts/load_market_data.py` - Chargement données market

### 2. Endpoints à tester

**API Health**:
```bash
curl http://localhost:8000/health
# Attendu: {"status": "ok", "service": "arquantix-api"}
```

**API Docs**:
```bash
curl http://localhost:8000/docs
# Attendu: Swagger UI HTML
```

**Web**:
```bash
curl http://localhost:3000
# Attendu: HTML Next.js
```

**DB**:
```bash
docker exec arquantix-db psql -U arquantix -d arquantix_quant -c "SELECT COUNT(*) FROM market_data_instruments;"
```

### 3. Pages à vérifier

**Ordre de vérification**:
1. `/admin/login` - Login fonctionne
2. `/admin` - Dashboard accessible
3. `/admin/finance` - Page Finance avec 3 tabs (Market Data, Bundles, Backtests)
4. `/admin/finance` → Tab "Market Data" - Instruments chargés, chart affiché
5. `/admin/finance` → Tab "Bundles" - Bundles chargés, création fonctionne
6. `/admin/finance` → Tab "Backtests" - Backtest peut être lancé

**Erreurs communes**:
- Menu admin manquant → Vérifier `web/src/app/admin/layout.tsx` (AdminSidebar intégré)
- Dropdowns transparents → Vérifier `web/src/components/ui/select.tsx` et `dropdown-menu.tsx` (`bg-white`)
- Bundles non chargés → Vérifier format réponse API (`{ bundles: [...] }` vs `[...]`)

### 4. Commandes utiles

**Démarrage complet**:
```bash
cd /path/to/arquantix
./scripts/arquantix-start.sh
```

**Vérifier status**:
```bash
curl http://localhost:8000/health  # API
curl http://localhost:3000          # Web
docker exec arquantix-db pg_isready -U arquantix  # DB
```

**Logs**:
```bash
tail -f /tmp/arquantix-api.log  # API
tail -f /tmp/arquantix-web.log  # Web
docker logs -f arquantix-db      # DB
```

**Arrêt**:
```bash
kill $(cat /tmp/arquantix-api.pid) 2>/dev/null
kill $(cat /tmp/arquantix-web.pid) 2>/dev/null
```

---

## 📝 LIMITATIONS ACTUELLES

### Non implémenté (vérifié)

- **Backtest asynchrone**: TODO dans `api/services/backtest/routes.py:151` (actuellement synchrone)
- **Bundle resolver (composite)**: UNKNOWN si implémenté (résolution bundles de bundles)
- **Bundles dynamiques**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si moteur d'exécution implémenté
- **Preview API bundles**: UNKNOWN si endpoint `/api/bundles/{id}/preview` existe

### Inconsistances

- **Migration `a39b971e0c8c`**: Crée table `market_data_bundles` non utilisée (table réelle: `bundles`)
- **Table `bundle_allocations`**: Orphane (existe mais non référencée dans le code)
- **Modèle vs DB**: Inconsistances nullable (voir `60_DATABASE_ALEMBIC.md` section 7)

---

## 🗺️ ROADMAP IMPLICITE

**Basée uniquement sur TODOs / code existant** :

1. **Backtest asynchrone**: TODO dans `api/services/backtest/routes.py:151`
   - "In production, this should be queued as an async task"

2. **Bundle resolver (composite)**: Structure DB existe (`bundle_components.child_bundle_id`), mais UNKNOWN si implémenté

3. **Bundles dynamiques**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si moteur d'exécution implémenté

**⚠️ Roadmap basée uniquement sur structure DB et TODOs trouvés. Aucune roadmap explicite trouvée dans le code.**

---

## 📖 NAVIGATION

- **Vue d'ensemble**: [00_OVERVIEW.md](canonical/00_OVERVIEW.md)
- **Frontend**: [10_FRONTEND_NEXTJS.md](canonical/10_FRONTEND_NEXTJS.md)
- **Backend**: [20_BACKEND_FASTAPI.md](canonical/20_BACKEND_FASTAPI.md)
- **Market Data**: [30_MARKET_DATA.md](canonical/30_MARKET_DATA.md)
- **Bundles**: [40_BUNDLES.md](canonical/40_BUNDLES.md)
- **Backtests**: [50_BACKTESTS.md](canonical/50_BACKTESTS.md)
- **Database**: [60_DATABASE_ALEMBIC.md](canonical/60_DATABASE_ALEMBIC.md)
- **Runbook Dev**: [70_RUNBOOK_DEV.md](canonical/70_RUNBOOK_DEV.md)

---

**Dernière mise à jour**: 2026-01-10  
**Auteur**: Documentation automatique basée sur codebase  
**Version**: 1.0.0


