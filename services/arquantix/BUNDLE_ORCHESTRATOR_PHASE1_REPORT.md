# BUNDLE ORCHESTRATOR — PHASE 1 REPORT

## Executive Summary

Phase 1 du Bundle Allocation Engine est implémentée. Le `BundleOrchestrator` fait le pont entre le Portfolio Engine (PE) et l'Exchange Engine pour exécuter des investissements dans des bundles crypto. 

### Réalisations

- **Entry asset configuration** : `entry_asset_default` et `entry_assets_allowed` ajoutés au schéma `BundleCreate` et persistés dans `ProductDefinition.metadata_`
- **BundleOrchestrator** : nouveau service qui orchestre le funding et l'allocation initiale
- **Funding EUR** : allocation directe via `ExchangeService.buy()` pour chaque asset cible
- **Funding crypto** : support SWAP via `ExchangeService.swap()` pour allocation depuis un entry asset crypto
- **Sync PE ↔ Exchange** : les `exchange_orders` sont tagués avec `bundle_id` dans `metadata_`, les `pe_position_atoms` sont créés/mis à jour
- **Invariant D** : `Σ pe_atoms.quantity ≤ crypto_positions.balance` — implémenté et testé
- **8 tests** passent (8/8), incluant non-régression
- **0 migration DB** requise
- **0 modification** au moteur Exchange core

---

## Entry Asset Configuration

### Schéma

Deux nouveaux champs ajoutés à `BundleCreate` (schemas.py) :

```python
entry_asset_default: str = Field(default="USDC", max_length=20)
entry_assets_allowed: list[str] = Field(default_factory=lambda: ["USDC"])
```

### Persistance

Stockés dans `ProductDefinition.metadata_` (JSONB) :

```json
{
  "entry_asset_default": "USDC",
  "entry_assets_allowed": ["USDC", "EURC"],
  "available_rebalance_frequencies": ["monthly"]
}
```

### Validation

Le `BundleOrchestrator` valide que le `funding_asset` est soit :
- `EUR` ou `USD` (fiat — toujours accepté)
- Un asset listé dans `entry_assets_allowed`

---

## Backward Compatibility for Existing Bundles

### Stratégie de fallback

Si `entry_asset_default` ou `entry_assets_allowed` sont absents du metadata :

| Champ | Fallback |
|-------|----------|
| `entry_asset_default` | `"USDC"` |
| `entry_assets_allowed` | `["USDC"]` |

Le fallback est appliqué dans `_resolve_entry_config()`.

### Test validé

`test_fallback_entry_asset_when_not_configured` : un bundle créé sans config entry_asset utilise correctement le fallback USDC.

### Impact sur les bundles existants

**Aucun**. Les champs sont ajoutés au schéma `BundleCreate` avec des valeurs par défaut. Les bundles existants dans la DB ont leur `metadata_` inchangée ; le fallback garantit la compatibilité.

---

## BundleOrchestrator Design

### Fichier

`api/services/portfolio_engine/bundles/orchestrator.py`

### Architecture

```
BundleOrchestrator.invest_into_bundle()
  │
  ├── 1. Validate portfolio (type=bundle_portfolio, status=active, client match)
  ├── 2. Load product → resolve entry_config
  ├── 3. Validate funding_asset against allowed list
  ├── 4. Load target_allocations for portfolio
  ├── 5. For each allocation leg:
  │     ├── Calculate amount = funding_amount × target_weight
  │     ├── Execute via Exchange Engine (BUY or SWAP)
  │     ├── Tag exchange_order with bundle_id in metadata_
  │     └── Sync pe_position_atoms (create or update)
  ├── 6. Handle partial failures (best-effort strategy)
  ├── 7. Audit log
  └── 8. Return structured result
```

### Principes

- L'orchestrateur ne remplace pas l'Exchange Engine, il le **pilote**
- Stratégie **best-effort** : si une jambe échoue, les autres continuent
- Chaque exécution réussie est suivie immédiatement d'une sync PE
- Batch identifié par `batch_id` UUID unique

---

## Funding Flow

### Cas 1 — Client apporte EUR

```
EUR → ExchangeService.buy(asset=BTC, fiat_amount=700€) → crypto_positions[BTC] += X
EUR → ExchangeService.buy(asset=ETH, fiat_amount=300€) → crypto_positions[ETH] += Y
```

Pas d'intermédiaire. L'orchestrateur calcule `amount_per_leg = funding_amount × target_weight` et lance un BUY direct pour chaque asset cible.

### Cas 2 — Client possède déjà un entry asset (crypto)

```
USDC → ExchangeService.swap(from=USDC, to=BTC, amount=700) → crypto_positions[BTC] += X
USDC → ExchangeService.swap(from=USDC, to=ETH, amount=300) → crypto_positions[ETH] += Y
```

Requiert que l'entry asset soit dans `SUPPORTED_ASSETS` avec market data. Pour Phase 1, le funding EUR est la voie principale. Le support USDC/EURC sera activé quand ces assets seront ajoutés au moteur Exchange.

---

## Initial Allocation Flow

### Calcul des montants

```python
alloc_amount = (funding_amount × target_weight).quantize(0.01, ROUND_DOWN)
```

Exemple avec 1000€ et allocation BTC 70% / ETH 30% :
- BTC : 700.00€
- ETH : 300.00€

### Exécution

Séquentielle, par ordre de `rebalance_priority` (ASC). Chaque jambe est indépendante.

### Résultat type

```json
{
  "status": "completed",
  "batch_id": "uuid",
  "portfolio_id": "uuid",
  "entry_asset_used": "EUR",
  "total_input_amount": 1000.0,
  "total_allocated": 1000.0,
  "remaining_entry_asset": 0.0,
  "legs_succeeded": 2,
  "legs_failed": 0,
  "execution_details": [
    {
      "asset": "BTC",
      "target_weight": 0.7,
      "amount_allocated": 700.0,
      "crypto_received": 0.00822...,
      "status": "completed",
      "order_id": "uuid"
    },
    {
      "asset": "ETH",
      "target_weight": 0.3,
      "amount_allocated": 300.0,
      "crypto_received": 0.1303...,
      "status": "completed",
      "order_id": "uuid"
    }
  ]
}
```

### Gestion des échecs partiels

Si une jambe échoue (ex: quote stale) :
- Les jambes réussies sont conservées
- La jambe échouée est reportée avec `status: "failed"` et `error`
- Le status global passe à `"partial"`
- Le reliquat reste calculé dans `remaining_entry_asset`
- Le bundle reste cohérent : seules les jambes réussies ont des `pe_position_atoms`

---

## PE ↔ Exchange Synchronization

### Tagging des exchange_orders

Après chaque exécution réussie, le `metadata_` JSONB de l'ExchangeOrder est enrichi :

```json
{
  "bundle_id": "portfolio-uuid",
  "bundle_batch_id": "batch-uuid",
  "bundle_action": "initial_allocation"
}
```

Cela permet de filtrer les ordres bundle pour :
- Calcul PnL bundle (futur)
- Audit / traçabilité
- Wallet history filtrée

### Sync pe_position_atoms

Après chaque BUY/SWAP réussi :

1. Recherche d'un `PositionAtom` existant pour `(portfolio_id, instrument_id, status=open)`
2. Si trouvé : mise à jour `quantity`, `available_quantity`, `cost_basis`, `average_entry_price`
3. Si absent : création d'un nouveau `PositionAtom` avec `position_type=spot`

### Cohérence

La sync est effectuée dans la même transaction que l'exécution Exchange. En cas d'échec de la sync (erreur DB), la jambe entière est marquée failed et la transaction reste cohérente.

---

## Invariant D Validation

### Définition

```
Invariant D : ∀ asset, Σ pe_position_atoms.quantity ≤ crypto_positions.balance
```

Le total des quantités allouées dans le PE ne doit jamais dépasser la position consolidée Exchange.

### Implémentation

`BundleOrchestrator.check_invariant_d(db, client_id)` :

1. Agrège les `pe_position_atoms` par symbole d'asset (via `Instrument → Asset`)
2. Compare avec `crypto_positions.balance` pour le même client
3. Retourne `invariant_d_ok: bool` et la liste des violations

### API

```
GET /api/app/bundle/invariant-d
```

### Test

`test_invariant_d_holds` : après investissement dans un bundle, l'invariant D est vérifié sans violation.

---

## Tests Added

| # | Test | Statut |
|---|------|--------|
| 1 | `test_fallback_entry_asset_when_not_configured` | ✅ PASS |
| 2 | `test_invest_eur_into_bundle` | ✅ PASS |
| 3 | `test_invest_unsupported_entry_asset_fails_gracefully` | ✅ PASS |
| 4 | `test_partial_failure_keeps_bundle_coherent` | ✅ PASS |
| 5 | `test_pe_exchange_sync` | ✅ PASS |
| 6 | `test_invariant_d_holds` | ✅ PASS |
| 7 | `test_non_regression_exchange_operations` | ✅ PASS |
| 8 | `test_entry_asset_stored_in_product_metadata` | ✅ PASS |

### Non-régression

| Suite | Résultat |
|-------|----------|
| `test_bundle_engine.py` | 54 passed ✅ |
| `test_bundle_engine_provisioning_e2e.py` | 2 passed ✅ |
| `test_bundle_orchestrator.py` | 8 passed ✅ |

---

## Files Modified / Created

### Modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/portfolio_engine/bundles/schemas.py` | Ajout `entry_asset_default`, `entry_assets_allowed` à `BundleCreate` |
| `api/services/portfolio_engine/bundles/service.py` | Persistance entry_asset dans `ProductDefinition.metadata_` |
| `api/services/test_clients/router.py` | Ajout endpoints `/bundle/invest` et `/bundle/invariant-d` |

### Créés

| Fichier | Rôle |
|---------|------|
| `api/services/portfolio_engine/bundles/orchestrator.py` | BundleOrchestrator — service principal Phase 1 |
| `api/tests/test_bundle_orchestrator.py` | 8 tests Phase 1 |

### Non modifiés (contrainte respectée)

- `api/services/exchange/service.py` — Exchange Engine INCHANGÉ
- `api/services/exchange/models.py` — CryptoPosition / ExchangeOrder INCHANGÉS
- `api/services/exchange/repository.py` — INCHANGÉ
- `api/services/exchange/schemas.py` — INCHANGÉ
- `api/services/wallet_statistics/service.py` — INCHANGÉ
- `api/services/accounting/invariants.py` — INCHANGÉ (invariants A/B/C intacts)

### Pas de migration DB

Aucune migration Alembic créée. Tout repose sur :
- JSONB `metadata_` existant sur `ProductDefinition`
- JSONB `metadata_` existant sur `ExchangeOrder`
- Tables PE existantes (`pe_position_atoms`, `pe_portfolios`, etc.)

---

## Final Status

| Critère | Statut |
|---------|--------|
| Entry asset config | ✅ Implémenté |
| Backward compatibility | ✅ Fallback USDC |
| BundleOrchestrator | ✅ Créé |
| Funding EUR → BUY | ✅ Fonctionnel |
| Funding crypto → SWAP | ✅ Code prêt (nécessite entry asset dans SUPPORTED_ASSETS) |
| Allocation initiale | ✅ Séquentielle, best-effort |
| PE ↔ Exchange sync | ✅ Tagging + atoms |
| Invariant D | ✅ Implémenté + testé |
| API endpoint | ✅ `/bundle/invest` + `/bundle/invariant-d` |
| Tests (8/8) | ✅ Tous passent |
| Non-régression | ✅ 54 + 2 tests existants intacts |
| Exchange Engine inchangé | ✅ Aucune modification |
| WAC/PnL inchangé | ✅ Aucune modification |
| Invariants A/B/C intacts | ✅ Aucune modification |
| Migration DB | ✅ Aucune requise |
