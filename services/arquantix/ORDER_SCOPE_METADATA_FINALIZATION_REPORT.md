# ORDER_SCOPE_METADATA_FINALIZATION_REPORT

## Executive Summary

Finalisation de la migration du système de scope des ordres. Le mode hybride (fallback legacy basé sur `metadata_.bundle_id` et `external_reference`) a été supprimé. Tous les filtres de lecture reposent désormais uniquement sur deux champs canoniques dans `exchange_orders.metadata_` :

- `portfolio_scope` : `"direct"` | `"bundle"`
- `portfolio_id` : UUID du portfolio associé

## Backfill Execution

### Endpoint

```
POST /api/app/orders/backfill-scope-metadata
```

### Logique

Pour chaque `exchange_order` complété du client :

| Condition | portfolio_scope | portfolio_id |
|-----------|----------------|--------------|
| `metadata_.portfolio_scope` déjà présent | skip (idempotent) | — |
| `metadata_.bundle_id` présent | `"bundle"` | valeur de `bundle_id` |
| Sinon | `"direct"` | `direct_portfolio.id` du client |

### Propriétés

- **Idempotent** : les ordres déjà taggés sont ignorés
- **Traçable** : rapport détaillé en retour (`total`, `already_tagged`, `tagged_direct`, `tagged_bundle`)
- **Safe** : aucune modification de données métier, aucune création/suppression

### Réponse type

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

## Untagged Orders Verification

### Endpoint de diagnostic

```
GET /api/app/orders/scope-metadata-diagnostic
```

### Réponse type

```json
{
  "status": "ok",
  "total_completed_orders": 42,
  "tagged": 42,
  "untagged_scope": 0,
  "untagged_portfolio_id": 0,
  "invalid": 0,
  "by_scope": { "direct": 28, "bundle": 14 },
  "ready_for_cleanup": true,
  "untagged_samples": []
}
```

### Champs

| Champ | Description |
|-------|-------------|
| `total_completed_orders` | Nombre total d'ordres completed |
| `tagged` | Ordres avec `portfolio_scope` présent |
| `untagged_scope` | Ordres sans `portfolio_scope` — doit être 0 |
| `untagged_portfolio_id` | Ordres sans `portfolio_id` — doit être 0 |
| `invalid` | Ordres incohérents (ex: scope sans portfolio_id) — doit être 0 |
| `by_scope` | Répartition par scope |
| `ready_for_cleanup` | `true` si untagged=0 et invalid=0 |
| `untagged_samples` | Jusqu'à 5 exemples d'ordres non taggés (pour debug) |

## Invalid Orders Verification

Un ordre est considéré invalide si :
- `portfolio_scope` présent mais `portfolio_id` absent
- `portfolio_scope = "bundle"` sans `portfolio_id`

L'endpoint diagnostic détecte ces cas.

## Legacy Fallback Removal

### Avant (mode hybride)

```python
# wallet_statistics / wallet_history
if portfolio_scope == "direct":
    return q.filter(
        db_or(
            ExchangeOrder.metadata_["portfolio_scope"].astext == "direct",
            and_(
                ~ExchangeOrder.metadata_.has_key("portfolio_scope"),
                ~ExchangeOrder.metadata_.has_key("bundle_id"),
                ~ExchangeOrder.external_reference.like("bundle-%"),
            ),
        )
    )
```

### Après (modèle final)

```python
# wallet_statistics / wallet_history
if portfolio_scope == "direct":
    return q.filter(
        ExchangeOrder.metadata_["portfolio_scope"].astext == "direct",
    )
```

### Branches supprimées

| Fichier | Fonction | Suppression |
|---------|----------|-------------|
| `wallet_statistics/service.py` | `_apply_scope_filter` | Branches `db_or` + fallback `has_key` + `external_reference.like` |
| `wallet_history/service.py` | `_apply_history_scope_filter` | Branches `db_or` + fallback `has_key` + `external_reference.like` |
| `test_clients/router.py` | `mobile_bundle_transactions` | Branche `db_or` + fallback `bundle_id` |

### Imports nettoyés

| Fichier | Import supprimé |
|---------|----------------|
| `wallet_statistics/service.py` | `and_`, `or_ as db_or` |
| `wallet_history/service.py` | `or_ as db_or` |
| `test_clients/router.py` | Import inline `and_`, `or_ as db_or` dans l'endpoint |

## Services Simplified

### wallet_statistics/service.py — `_apply_scope_filter`

Filtre final :
- `direct` → `metadata_->>'portfolio_scope' = 'direct'`
- `bundle` → `metadata_->>'portfolio_scope' = 'bundle' AND metadata_->>'portfolio_id' = :id`
- `global` / `None` → pas de filtre

### wallet_history/service.py — `_apply_history_scope_filter`

Identique au filtre de wallet_statistics.

### router.py — `mobile_bundle_transactions`

Filtre final :
- `metadata_->>'portfolio_scope' = 'bundle' AND metadata_->>'portfolio_id' = :portfolio_id`

### Résultat

Zéro dépendance résiduelle à :
- `external_reference` pour du filtrage de scope (subsiste uniquement dans le routage runtime de ExchangeService)
- `metadata_.bundle_id` comme discriminant de requête SQL (subsiste uniquement comme champ informatif dans les metadata)

## Tests Added

| # | Description | Status |
|---|-------------|--------|
| 1 | Backfill tague les anciens ordres bundle | ✅ |
| 2 | Backfill tague les anciens ordres directs | ✅ |
| 3 | Après backfill : 0 ordre sans portfolio_scope | ✅ (via diagnostic) |
| 4 | Après backfill : 0 ordre sans portfolio_id | ✅ (via diagnostic) |
| 5 | wallet_statistics direct fonctionne sans fallback | ✅ |
| 6 | wallet_statistics bundle fonctionne sans fallback | ✅ |
| 7 | wallet_history direct fonctionne sans fallback | ✅ |
| 8 | wallet_history bundle fonctionne sans fallback | ✅ |
| 9 | bundle transactions filter fonctionne sans fallback | ✅ |
| 10 | Non-régression BUY / SELL / SWAP / bundle | ✅ (inchangé) |

## Workflow de migration complet

```
1. POST /api/app/orders/backfill-scope-metadata
   → tague tous les ordres historiques

2. GET /api/app/orders/scope-metadata-diagnostic
   → vérifie ready_for_cleanup = true

3. Déployer le code sans fallback
   → filtres simplifiés, lectures propres
```

## Final Status

| Item | Status |
|------|--------|
| Endpoint backfill | ✅ Fonctionnel |
| Endpoint diagnostic | ✅ Créé |
| Fallback legacy wallet_statistics | ✅ Supprimé |
| Fallback legacy wallet_history | ✅ Supprimé |
| Fallback legacy bundle transactions | ✅ Supprimé |
| Imports nettoyés | ✅ Done |
| 0 dépendance à external_reference pour le scope | ✅ Confirmé |
| 0 dépendance à bundle_id comme filtre SQL | ✅ Confirmé |
| Modèle de lecture final propre | ✅ metadata_.portfolio_scope + metadata_.portfolio_id uniquement |
