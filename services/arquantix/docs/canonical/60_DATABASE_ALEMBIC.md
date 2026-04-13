# Base de données & Migrations Alembic

**Fichiers clés**: `api/database.py`, `api/alembic/versions/*.py`, `api/scripts/seed.py`

---

## 1. Tables clés

### Liste exhaustive (vérifiée dans DB)

**Market Data**:
- `market_data_instruments` - Instruments (symbol, asset_class, provider, etc.)
- `market_data_bars_d1` - Bars OHLCV quotidiennes (PK: `instrument_id`, `date`)

**Bundles**:
- `bundles` - Bundles (name, asset_class, type, description)
- `bundle_components` - Composants bundles (instrument ou bundle enfant, weight)
- `bundle_allocations` - **ORPHANE** (existe mais non utilisée dans le code)
- `bundle_dynamic_rules` - Règles dynamiques pour bundles `dynamic`

**Backtests**:
- `backtest_runs` - Runs de backtest (paramètres, status)
- `backtest_portfolio_series` - Séries portfolio (NAV, returns, drawdown, turnover, costs)
- `backtest_instrument_series` - Séries par instrument (base100, returns)
- `backtest_metrics` - Métriques (total_return, sharpe, max_drawdown, etc.)

**Admin/CMS**:
- `admin_users` - Utilisateurs admin (email, hashed_password)
- `global_settings` - Paramètres globaux
- `pages` - Pages CMS (slug, locale, sections_json)
- `news` - Articles/news (slug, locale, content_markdown)

**Email**:
- `email_modules` - Modules email
- `email_module_i18n` - Traductions modules email
- `email_template_entities` - Templates email

**Référence**: Tables vérifiées via `docker exec arquantix-db psql -U arquantix -d arquantix -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"`

---

## 2. Relations

### Market Data

```
market_data_instruments (1) ──< (N) market_data_bars_d1
  - FK: market_data_bars_d1.instrument_id → market_data_instruments.id
```

### Bundles

```
bundles (1) ──< (N) bundle_components
  - FK: bundle_components.bundle_id → bundles.id

bundles (1) ──< (N) bundle_components (child_bundle_id)
  - FK: bundle_components.child_bundle_id → bundles.id (self-reference)

market_data_instruments (1) ──< (N) bundle_components
  - FK: bundle_components.instrument_id → market_data_instruments.id

bundles (1) ──< (N) bundle_allocations
  - FK: bundle_allocations.bundle_id → bundles.id (ORPHANE, non utilisée)

bundles (1) ──< (N) bundle_dynamic_rules
  - FK: bundle_dynamic_rules.bundle_id → bundles.id
```

### Backtests

```
backtest_runs (1) ──< (N) backtest_portfolio_series
  - FK: backtest_portfolio_series.run_id → backtest_runs.id

backtest_runs (1) ──< (N) backtest_instrument_series
  - FK: backtest_instrument_series.run_id → backtest_runs.id

backtest_runs (1) ──< (N) backtest_metrics
  - FK: backtest_metrics.run_id → backtest_runs.id

market_data_instruments (1) ──< (N) backtest_instrument_series
  - FK: backtest_instrument_series.instrument_id → market_data_instruments.id

market_data_instruments (1) ──< (N) backtest_metrics
  - FK: backtest_metrics.instrument_id → market_data_instruments.id (nullable)

bundles (1) ──< (N) backtest_runs (nullable)
  - FK: backtest_runs.bundle_id → bundles.id (ON DELETE SET NULL)
```

**Référence**: Contraintes vérifiées via `\d table_name` dans PostgreSQL

---

## 3. Contraintes importantes

### `bundles.type` (CHECK)

```sql
chk_bundles_type_valid: CHECK (type IN ('fixed_instruments', 'composite_fixed', 'dynamic'))
```

**Vérifié**: DB via `pg_get_constraintdef`

**Valeur par défaut**: `'FIXED_WEIGHT'` (mais CHECK refuse cette valeur → **INCONSISTANCE**)

**Fix appliqué**: Utilisation de `'fixed_instruments'` dans le code.

**Référence**: `api/services/bundles/routes.py:194-198`

### `bundle_components` (XOR)

```sql
chk_bundle_components_xor: CHECK (
  (component_type = 'instrument' AND instrument_id IS NOT NULL AND child_bundle_id IS NULL)
  OR
  (component_type = 'bundle' AND child_bundle_id IS NOT NULL AND instrument_id IS NULL)
)
```

**Vérifié**: DB via `\d bundle_components`

**Implication**: Un `BundleComponent` est soit un instrument, soit un bundle enfant (pas les deux).

### `bundle_components.weight` (>= 0)

```sql
chk_bundle_components_weight_non_negative: CHECK (weight >= 0)
```

**Vérifié**: DB

### `market_data_bars_d1` (PK composite)

**PK**: `(instrument_id, date)`

**Uniqueness**: Une seule barre par instrument et date.

**Référence**: `api/database.py:138-139`

### `backtest_metrics` (PK + UNIQUE)

**PK**: `id` (serial, ajouté dans migration `a8723d70ea70`)

**UNIQUE**: `(run_id, scope, instrument_id, key)` (permet `instrument_id = NULL` pour métriques portfolio)

**Référence**: Migration `api/alembic/versions/a8723d70ea70_fix_backtest_metrics_pk_allow_null_.py`

---

## 4. Migrations Alembic critiques

### Ordre des migrations (vérifié)

1. `001_initial` - Tables de base (admin_users, global_settings, pages, news)
2. `002_add_translation_fields` - Champs traduction pages
3. `cc6123cabd3c_add_email_tables` - Tables email
4. `dd7124eabc4d_add_market_data_tables` - `market_data_instruments`, `market_data_bars_d1`
5. `ee8235fabc5e_add_backtest_tables` - Tables backtest
6. `a8723d70ea70_fix_backtest_metrics_pk_allow_null_` - Fix PK `backtest_metrics` (allow NULL `instrument_id`)
7. `a39b971e0c8c_add_composite_and_dynamic_bundles` - **PROBLÈME**: Crée table `market_data_bundles` (non utilisée)

**Référence**: `api/alembic/versions/*.py`

### Migration `dd7124eabc4d_add_market_data_tables`

**Objectif**: Créer tables market data.

**Tables créées**:
- `market_data_instruments` (id, symbol, name, asset_class, weekend_tradable, provider, provider_symbol, is_active, created_at)
- `market_data_bars_d1` (PK: instrument_id, date; open, high, low, close, volume, source, created_at)

**Référence**: `api/alembic/versions/dd7124eabc4d_add_market_data_tables.py`

### Migration `ee8235fabc5e_add_backtest_tables`

**Objectif**: Créer tables backtest.

**Tables créées**:
- `backtest_runs` (id, name, start_date, end_date, rebalance, strategy_type, fees_bps, slippage_bps, instrument_ids_json, status)
- `backtest_portfolio_series` (PK: run_id, date; nav_base100, portfolio_return, drawdown, turnover, costs, weights_json, tradable_json)
- `backtest_instrument_series` (PK: run_id, instrument_id, date; base100, instrument_return)
- `backtest_metrics` (PK original: run_id, scope, instrument_id, key; value)

**Référence**: `api/alembic/versions/ee8235fabc5e_add_backtest_tables.py`

### Migration `a8723d70ea70_fix_backtest_metrics_pk_allow_null_`

**Objectif**: Permettre `instrument_id = NULL` dans `backtest_metrics` (pour métriques portfolio).

**Changements**:
1. Ajout colonne `id` (serial) comme nouvelle PK
2. Drop ancienne PK `(run_id, scope, instrument_id, key)`
3. Make `instrument_id` nullable
4. Create nouvelle PK sur `id`
5. Create UNIQUE constraint sur `(run_id, scope, instrument_id, key)` (PostgreSQL permet NULL dans UNIQUE)

**Référence**: `api/alembic/versions/a8723d70ea70_fix_backtest_metrics_pk_allow_null_.py`

### Migration `a39b971e0c8c_add_composite_and_dynamic_bundles`

**⚠️ PROBLÈME**: Crée table `market_data_bundles` avec structure différente de `bundles` actuelle.

**Table créée**: `market_data_bundles` (id String UUID, name, description, instrument_ids JSON, created_at, updated_at)

**Status**: Table non utilisée dans le code (table réelle: `bundles` avec structure différente).

**Incohérence**: Migration crée une table qui n'est pas utilisée.

**Référence**: `api/alembic/versions/a39b971e0c8c_add_composite_and_dynamic_bundles.py`

---

## 5. Seeds / Fixtures

### Script seed (`api/scripts/seed.py`)

**Usage**: `python scripts/seed.py`

**Données créées**:
1. **Admin user**: Email `ADMIN_EMAIL` (défaut: `"admin@arquantix.com"`), password `ADMIN_PASSWORD` (défaut: `"admin123"`)
2. **Global settings**: `site_name="Arquantix"`, `tagline="Innovation Technology"`, `socials_json={}`, `seo_json={}`

**Référence**: `api/scripts/seed.py:14-211`

**Variables d'environnement**:
- `ADMIN_EMAIL` - Email admin (défaut: `"admin@arquantix.com"`)
- `ADMIN_PASSWORD` - Password admin (défaut: `"admin123"`)

**Référence**: `api/scripts/seed.py:18-19`

### Script load_market_data (`api/scripts/load_market_data.py`)

**Usage**: `python scripts/load_market_data.py [--all] [--update-recent] [--instrument-id ID] [--force-full]`

**Fonction**: Charge données historiques depuis Yahoo Finance dans `market_data_bars_d1`.

**CORE_V1_INSTRUMENTS**: Crée instruments de base si inexistants (BTC, ETH, SOL, URTH, QQQ, DIA, GLD).

**Référence**: `api/scripts/load_market_data.py`, `api/services/market_data/routes.py:19-27`

---

## 6. Schéma de base de données

**Nom**: `arquantix` (base unique partagée avec Prisma ; anciennement `arquantix_quant`)

**Schéma**: `public`

**Host**: `localhost` (ou container `arquantix-db`)

**Port**: `5443` (mappé depuis 5432 du container)

**User**: `arquantix`

**Password**: `arquantix` (défaut, vérifier `.env.local`)

**Référence**: `api/database.py:23-26`, `scripts/arquantix-start.sh:94`

---

## 7. Inconsistances modèle vs DB

### `bundles.asset_class`

**Modèle SQLAlchemy**: `nullable=True`

**DB réelle**: `NOT NULL`

**Impact**: Erreur `NotNullViolation` si non défini lors de la création.

**Fix appliqué**: Calcul de `asset_class` depuis instruments sélectionnés.

**Référence**: `api/services/bundles/routes.py:180-189`

### `bundles.type`

**Modèle SQLAlchemy**: `nullable=True`

**DB réelle**: `NOT NULL` avec CHECK `chk_bundles_type_valid`

**Valeur par défaut DB**: `'FIXED_WEIGHT'` (mais CHECK refuse cette valeur).

**Fix appliqué**: Utilisation de `'fixed_instruments'` dans le code.

**Référence**: `api/services/bundles/routes.py:194-198`

### `bundle_components.weight`

**Modèle SQLAlchemy**: `nullable=True`

**DB réelle**: `NOT NULL`

**Impact**: Erreur si `weight` non défini (mais validation frontend garantit 100%).

**Référence**: Contrainte vérifiée dans DB

---

## 8. Index importants

### `market_data_bars_d1`

- `ix_market_data_bars_d1_instrument_id` - Sur `instrument_id`
- `ix_market_data_bars_d1_date` - Sur `date`

**Usage**: Requêtes par instrument et date (charts, backtests).

**Référence**: `api/alembic/versions/dd7124eabc4d_add_market_data_tables.py:56-57`

### `bundles`

- `ix_bundles_id` - Sur `id`
- `ix_bundles_asset_class_is_active` - Sur `(asset_class, is_active)`
- `uq_bundles_name_asset_class` - UNIQUE sur `(name, asset_class)`

**Référence**: Index vérifiés dans DB

---

## 9. Limitations / Incohérences

- **Migration `a39b971e0c8c`**: Crée table `market_data_bundles` non utilisée (table réelle: `bundles`)
- **Table `bundle_allocations`**: Orphane (existe mais non référencée dans le code)
- **Inconsistances nullable**: Modèle SQLAlchemy vs DB réelle (voir section 7)


