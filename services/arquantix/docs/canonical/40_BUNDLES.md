# Bundles — Concepts & Types

**Fichiers clés**: `api/services/bundles/routes.py`, `api/database.py:151-185`

---

## 1. Concept

### Définition

Un **bundle** est un **portefeuille d'instruments** avec allocations définies. Les bundles sont utilisés pour :

- **Stratégies figées**: Allocations fixes (ex: 80% BTCUSD, 20% ETHUSD)
- **Backtests**: Utilisation automatique des allocations lors d'un backtest (`strategy_type = "bundle_strategy"`)

**Important**: Un bundle = stratégie figée (allocation définie à la création, non modifiable dynamiquement sauf édition explicite).

**Référence**: `api/services/bundles/routes.py:159-293`

---

## 2. Types de bundles

### Contrainte CHECK

La colonne `type` dans la table `bundles` a une contrainte CHECK :

```sql
chk_bundles_type_valid: CHECK (type IN ('fixed_instruments', 'composite_fixed', 'dynamic'))
```

**Vérifié**: `docker exec arquantix-db psql -U arquantix -d arquantix_quant -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'public.bundles'::regclass AND contype = 'c';"`

### `fixed_instruments` (type actuel)

**Définition**: Bundle composé d'instruments directs avec allocations fixes.

**Implémentation actuelle**: Tous les bundles créés via l'UI sont de type `fixed_instruments`.

**Exemple**:
- Bundle "TOP2 Crypto"
  - BTCUSD: 80%
  - ETHUSD: 20%

**Référence**: `api/services/bundles/routes.py:194-198`

### `composite_fixed` (supporté dans DB, UNKNOWN si implémenté)

**Définition**: Bundle de bundles (bundle composite).

**Structure**: `bundle_components.component_type = 'bundle'`, `child_bundle_id` référence un autre bundle.

**Exemple**:
- Bundle "Mixed Portfolio"
  - Bundle "Crypto 60%" (enfant): 60%
  - Bundle "ETF 40%" (enfant): 40%

**Table**: `bundle_components` avec FK `child_bundle_id` vers `bundles(id)`.

**Status**: Table et contraintes existent, mais UNKNOWN si le resolver est implémenté.

**Référence**: `api/database.py:176-178`, contrainte XOR `chk_bundle_components_xor`

### `dynamic` (supporté dans DB, UNKNOWN si implémenté)

**Définition**: Bundle avec règles dynamiques (rules-based).

**Structure**: Table `bundle_dynamic_rules` avec `rule_type = 'formula_dsl'`, `rule_json`.

**Exemple**: UNKNOWN (non vérifié dans le code).

**Status**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si le moteur d'exécution est implémenté.

**Référence**: Table `bundle_dynamic_rules` vérifiée dans DB

---

## 3. Tables

### `bundles` (`api/database.py:151-165`)

```python
class MarketDataBundle(Base):
    __tablename__ = "bundles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    asset_class = Column(String(20), nullable=True)  # Mais NOT NULL en DB
    type = Column(String(50), nullable=True)  # CHECK constraint en DB
    description = Column(Text, nullable=True)
    is_active = Column(String(10), nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    created_by_email = Column(String(255), nullable=True)
```

**Contraintes DB** (vérifiées):
- `asset_class` NOT NULL (mais modèle SQLAlchemy autorise `nullable=True` → **INCONSISTANCE**)
- `type` NOT NULL avec CHECK `chk_bundles_type_valid` (`'fixed_instruments'`, `'composite_fixed'`, `'dynamic'`)
- UNIQUE `(name, asset_class)`

**Référence**: DB vérifiée via `\d bundles`

### `bundle_components` (`api/database.py:168-185`)

```python
class BundleComponent(Base):
    __tablename__ = "bundle_components"
    
    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("public.bundles.id"), nullable=False, index=True)
    component_type = Column(String(20), nullable=True)  # "instrument" or "bundle"
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), nullable=True)
    child_bundle_id = Column(Integer, ForeignKey("public.bundles.id"), nullable=True)
    weight = Column(Numeric(10, 4), nullable=True)  # Allocation en pourcentage (0-100)
    position_order = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
```

**Contraintes DB** (vérifiées):
- **XOR**: `chk_bundle_components_xor` - `component_type = 'instrument'` → `instrument_id NOT NULL` ET `child_bundle_id IS NULL` OU inverse
- **Weight >= 0**: `chk_bundle_components_weight_non_negative`
- **UNIQUE**: `(bundle_id, component_type, instrument_id, child_bundle_id)`
- **Weight NOT NULL**: `weight NOT NULL` en DB (mais modèle SQLAlchemy autorise `nullable=True` → **INCONSISTANCE**)

**Référence**: DB vérifiée via `\d bundle_components`

### `bundle_allocations` (UNKNOWN si utilisée)

**Table existe** dans la DB mais **NON référencée** dans le code Python.

**Structure**:
- `id`, `bundle_id`, `instrument_id`, `weight`, `position_order`, `created_at`
- UNIQUE `(bundle_id, instrument_id)`
- `weight >= 0`

**Status**: Table orpheline (créée par migration mais non utilisée actuellement).

### `bundle_dynamic_rules` (UNKNOWN si utilisée)

**Table existe** dans la DB pour bundles `dynamic`.

**Structure**:
- `id`, `bundle_id`, `rule_type` (CHECK: `'formula_dsl'`), `rule_json` (JSON), `version`, `is_active`, `created_at`, `updated_at`

**Status**: Table existe, mais UNKNOWN si le moteur d'exécution est implémenté.

---

## 4. Bundle Components

### Validation stricte

**Contrainte XOR** (`chk_bundle_components_xor`):
```sql
(component_type = 'instrument' AND instrument_id IS NOT NULL AND child_bundle_id IS NULL)
OR
(component_type = 'bundle' AND child_bundle_id IS NOT NULL AND instrument_id IS NULL)
```

**Implication**: Un `BundleComponent` est soit un instrument, soit un bundle enfant (pas les deux, pas aucun).

**Référence**: Contrainte vérifiée dans DB

### Pondérations

**Champ**: `weight` (type: `Numeric(10, 4)`)

**Unité**: **Pourcentage (0-100)** lors de la création, stocké tel quel.

**Validation**:
- Total allocations doit être 100% (tolérance 0.01%)
- Chaque `instrument_id` doit avoir une allocation définie
- Si aucune allocation fournie → égal weight (100% / n instruments)

**Référence**: `api/services/bundles/routes.py:222-257`

**Exemple**:
- Bundle avec 2 instruments → si allocations manquantes → 50% / 50%

---

## 5. Resolver (UNKNOWN si implémenté)

### Fonction attendue: `resolve_bundle_effective_weights`

⚠️ **UNKNOWN (needs confirmation)**: Aucune fonction `resolve_bundle_effective_weights` trouvée dans le code.

**Comportement attendu** (hypothèse, non vérifié):
1. Résoudre bundles composites (bundle de bundles) en instruments finaux
2. Détecter cycles (bundle A → bundle B → bundle A)
3. Calculer allocations effectives (ex: Bundle A 60% → Bundle B 50% BTCUSD → Allocation effective: 30% BTCUSD)
4. Normaliser pour que la somme = 100%

**Status**: NON VÉRIFIÉ dans le code actuel.

---

## 6. Preview API

⚠️ **UNKNOWN (needs confirmation)**: Endpoint `/api/bundles/{id}/preview` non trouvé dans le code.

**Comportement attendu** (hypothèse, non vérifié):
- Input: `bundle_id`, `date` (optionnel)
- Output: Allocations effectives par instrument (après résolution si composite)
- Calcul: Dépendances marché (lookback, SMA, etc.) si bundle `dynamic`

**Status**: NON VÉRIFIÉ.

---

## 7. Création de bundle (workflow actuel)

**Fichier**: `api/services/bundles/routes.py:159-293`

### Workflow

1. **Validation instruments**: Tous les `instrument_ids` doivent exister
2. **Calcul `asset_class`**: Classe la plus commune parmi les instruments (ou "mixed" si aucun)
3. **Validation allocations**:
   - Si allocations fournies → total = 100% (tolérance 0.01%)
   - Tous les instruments doivent avoir une allocation
4. **Création bundle**: `type = "fixed_instruments"`, `asset_class` calculé
5. **Création components**: Un `BundleComponent` par instrument avec `weight` (allocation en pourcentage)

**Référence**: `api/services/bundles/routes.py:166-264`

### Exemple (code réel)

```python
# Bundle "TOP2 Crypto" avec BTCUSD 80%, ETHUSD 20%
bundle = MarketDataBundle(
    name="TOP2 Crypto",
    asset_class="crypto",  # Calculé depuis instruments
    type="fixed_instruments",
    ...
)

# Components
BundleComponent(bundle_id=1, component_type="instrument", instrument_id=11, weight=Decimal("80.0"))
BundleComponent(bundle_id=1, component_type="instrument", instrument_id=27, weight=Decimal("20.0"))
```

**Référence**: `api/services/bundles/routes.py:242-263`

---

## 8. Utilisation dans backtests

**Fichier**: `api/services/backtest/routes.py:78-111`

### Chargement allocations

Quand `bundle_id` est fourni dans `BacktestRunRequest`:

1. Query `bundle_components` où `bundle_id = ...` ET `component_type = 'instrument'`
2. Extraire `weight` (pourcentage 0-100)
3. Convertir en `bundle_allocations` dict: `{instrument_id: float(weight)}`
4. Forcer `strategy_type = "bundle_strategy"`

**Référence**: `api/services/backtest/routes.py:88-111`

### Exécution backtest

**Fichier**: `api/services/backtest/executor.py:93-120`

**Logique bundle_strategy**:
1. Si `total_allocation = 100%` → convertir en décimal (diviser par 100)
2. Sinon → normaliser pour que la somme = 1
3. Créer DataFrame avec poids fixes pour toutes les dates (stratégie statique)

**Référence**: `api/services/backtest/executor.py:93-120`

---

## 9. Limitations actuelles

- **Bundle resolver (composite)**: UNKNOWN si implémenté (résolution bundles de bundles)
- **Détection de cycles**: UNKNOWN si implémentée
- **Bundles dynamiques**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si moteur d'exécution implémenté
- **Table `bundle_allocations`**: Existe mais non utilisée (orphane)
- **Migration `a39b971e0c8c`**: Crée table `market_data_bundles` qui n'est pas utilisée (table réelle: `bundles`)


