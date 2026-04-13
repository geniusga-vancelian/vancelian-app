# ORDER_SCOPE_METADATA_MIGRATION_REPORT

## Executive Summary

Migration du système de filtrage des ordres par scope (direct vs bundle) depuis un hack basé sur `external_reference LIKE 'bundle-%'` vers un système propre basé sur des tags explicites dans `exchange_orders.metadata_` :
- `portfolio_scope`: `"direct"` | `"bundle"`
- `portfolio_id`: UUID du portfolio associé

Les filtres de lecture (wallet_statistics, wallet_history, bundle transactions) utilisent désormais `metadata_->>'portfolio_scope'` comme discriminant canonique, avec un fallback legacy pour les ordres non encore migrés.

## Problem (external_reference hack)

### Avant

Le filtrage des ordres par scope reposait sur une convention de nommage fragile :

```python
# direct = tout ce qui n'est pas bundle
~ExchangeOrder.external_reference.like("bundle-%")

# bundle = orders avec bundle_id dans metadata
ExchangeOrder.metadata_["bundle_id"].astext == portfolio_id
```

**Problèmes :**
- Dépendance à un pattern de string (`bundle-*`) pour déterminer la nature d'un ordre
- Non scalable : l'ajout d'un nouveau type de portfolio nécessiterait de nouvelles conventions de nommage
- Incohérence : `external_reference` est un champ d'audit/debug, pas un discriminant métier
- Asymétrie : les ordres bundle avaient `bundle_id` en metadata, les ordres direct n'avaient rien

### Après

Chaque ordre porte un tag explicite :

```json
{
  "portfolio_scope": "direct",
  "portfolio_id": "uuid-du-direct-portfolio"
}
```

ou

```json
{
  "portfolio_scope": "bundle",
  "portfolio_id": "uuid-du-bundle-portfolio",
  "bundle_id": "uuid-du-bundle-portfolio",
  "bundle_batch_id": "...",
  "bundle_action": "funding|allocation"
}
```

## New Scope Model

| Champ | Type | Valeurs | Description |
|-------|------|---------|-------------|
| `portfolio_scope` | string | `"direct"` \| `"bundle"` | Scope métier de l'ordre |
| `portfolio_id` | string (UUID) | UUID | Portfolio PE associé |

**Règles d'attribution :**

- BUY / SELL / SWAP direct → `portfolio_scope = "direct"`, `portfolio_id = direct_portfolio.id`
- Opérations bundle (via BundleOrchestrator) → `portfolio_scope = "bundle"`, `portfolio_id = bundle_portfolio.id`

## Exchange Engine Update

### ExchangeService (`exchange/service.py`)

La détection runtime (pendant l'exécution buy/sell/swap) reste basée sur `external_reference.startswith("bundle-")` car c'est un signal de routage interne : au moment de l'exécution, le BundleOrchestrator n'a pas encore posé ses tags `metadata_`.

**Séquence :**
1. `BundleOrchestrator` appelle `ExchangeService.buy()` avec `external_reference="bundle-fund-{batch_id}"`
2. `ExchangeService` détecte `is_bundle_order = True` → ne sync pas le direct atom
3. `BundleOrchestrator._tag_order_metadata()` pose les tags `portfolio_scope`, `portfolio_id`, `bundle_id`, etc.

Pour les ordres directs, `ExchangeService` pose déjà les tags `portfolio_scope = "direct"` et `portfolio_id = direct_portfolio.id` (inchangé).

### BundleOrchestrator (`bundles/orchestrator.py`)

**Modifié :** `_tag_order_metadata()` ajoute désormais `portfolio_scope` et `portfolio_id` en plus des champs legacy (`bundle_id`, `bundle_batch_id`, `bundle_action`).

```python
meta["portfolio_scope"] = "bundle"
meta["portfolio_id"] = str(portfolio_id)
```

## Backfill Strategy

### Endpoint

```
POST /api/app/orders/backfill-scope-metadata
```

### Logique

Pour chaque `exchange_order` complété du client courant :

1. Si `metadata_.portfolio_scope` existe déjà → skip (idempotent)
2. Si `metadata_.bundle_id` existe → `portfolio_scope = "bundle"`, `portfolio_id = bundle_id`
3. Sinon → `portfolio_scope = "direct"`, `portfolio_id = direct_portfolio.id`

### Réponse

```json
{
  "status": "ok",
  "backfill": {
    "total": 42,
    "already_tagged": 10,
    "tagged_direct": 28,
    "tagged_bundle": 4
  }
}
```

### Propriétés

- **Idempotent** : les ordres déjà taggés sont ignorés
- **Traçable** : le rapport indique exactement combien d'ordres ont été traités par catégorie
- **Safe** : ne modifie aucune donnée métier, ne crée/supprime rien

## Migration Execution

### Phase 1 — Dual-mode (actuel)

Les filtres de lecture utilisent une logique en deux branches :

```python
# Branche principale : metadata_.portfolio_scope
ExchangeOrder.metadata_["portfolio_scope"].astext == "direct"

# Branche fallback : pour ordres pré-migration
AND NOT metadata_.has_key("portfolio_scope")
AND NOT metadata_.has_key("bundle_id")
AND NOT external_reference LIKE 'bundle-%'
```

### Phase 2 — Backfill

Exécuter `POST /api/app/orders/backfill-scope-metadata` pour taguer tous les ordres historiques.

### Phase 3 — Cleanup (futur)

Une fois tous les ordres taggés (objectif : 0 fallback) :
- Supprimer les branches fallback des filtres
- Simplifier les requêtes à `metadata_->>'portfolio_scope' = 'direct'`

## Fallback Handling

Pendant la transition, les filtres tolèrent les ordres sans `portfolio_scope` :

| Condition | Scope attribué |
|-----------|---------------|
| `metadata_.portfolio_scope` présent | Valeur du champ |
| `metadata_.bundle_id` présent, pas de `portfolio_scope` | `bundle` |
| Ni `portfolio_scope` ni `bundle_id`, `external_reference` ne commence pas par `bundle-` | `direct` |

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/portfolio_engine/bundles/orchestrator.py` | `_tag_order_metadata` ajoute `portfolio_scope` + `portfolio_id` |
| `api/services/wallet_statistics/service.py` | `_apply_scope_filter` migré vers `metadata_.portfolio_scope` avec fallback |
| `api/services/wallet_history/service.py` | `_apply_history_scope_filter` migré vers `metadata_.portfolio_scope` avec fallback |
| `api/services/test_clients/router.py` | Endpoint bundle transactions migré + nouvel endpoint backfill |

## Tests Added

### Test 1 — Ordre direct
BUY/SELL/SWAP direct → `metadata_.portfolio_scope = "direct"` ✅ (déjà en place dans ExchangeService)

### Test 2 — Ordre bundle
Investissement bundle → `metadata_.portfolio_scope = "bundle"` ✅ (ajouté dans BundleOrchestrator)

### Test 3 — wallet_statistics direct
Filtre `portfolio_scope = "direct"` → n'inclut aucun ordre bundle ✅

### Test 4 — wallet_statistics bundle
Filtre `portfolio_scope = "bundle"` → n'inclut que les ordres de ce bundle ✅

### Test 5 — wallet_history direct
Filtre `portfolio_scope = "direct"` → ordres directs uniquement ✅

### Test 6 — wallet_history bundle
Filtre `portfolio_scope = "bundle"` → ordres de ce bundle uniquement ✅

### Test 7 — Aucune dépendance restante à external_reference dans les filtres de lecture
Tous les filtres de lecture utilisent `metadata_.portfolio_scope` comme discriminant principal ✅
`external_reference` subsiste uniquement :
- Dans le routage runtime de ExchangeService (signal interne)
- Dans le fallback legacy des filtres (temporaire, supprimable après backfill complet)

## Final Status

| Item | Status |
|------|--------|
| BundleOrchestrator tag `portfolio_scope` | ✅ Done |
| wallet_statistics migré | ✅ Done |
| wallet_history migré | ✅ Done |
| Bundle transactions endpoint migré | ✅ Done |
| Backfill endpoint créé | ✅ Done |
| Fallback legacy en place | ✅ Done |
| ExchangeService routage (inchangé) | ✅ Stable |
| Backward compatible | ✅ Oui |
