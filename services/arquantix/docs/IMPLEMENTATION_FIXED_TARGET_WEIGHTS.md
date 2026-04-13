# Implémentation - Fixed Target Weights Rebalancing

## Résumé

Implémentation complète du système de rebalancing avec target weights fixes pour les bundles. Les bundles définissent maintenant des allocations cibles fixes qui sont utilisées comme source de vérité lors du rebalancing.

## Rapport d'Audit

Voir `docs/AUDIT_REBALANCING.md` pour le rapport complet.

**Conclusion** : Le système actuel ne supportait PAS les target weights fixes. Les weights étaient recalculés à chaque rebalance selon la stratégie.

## Fichiers Modifiés/Créés

### Backend

1. **`api/database.py`**
   - Ajout `bundle_id` (FK nullable vers bundles)
   - Ajout `rebalance_mode` (VARCHAR(50), default 'strategy_based')

2. **`api/alembic/versions/h3456789012c_add_bundle_id_to_backtest_runs.py`** (NOUVEAU)
   - Migration pour ajouter `bundle_id` et `rebalance_mode`
   - Index sur `bundle_id`
   - FK constraint avec SET NULL on delete

3. **`api/services/backtest/engine.py`**
   - Ajout `compute_target_weights_fixed()` : Retourne les fixed weights du bundle
   - Modification `compute_target_weights()` : Accepte paramètre `fixed_weights` optionnel

4. **`api/services/backtest/routes.py`**
   - Résolution du bundle AVANT création du run
   - Validation stricte : weights doivent sommer à 100% (REJET si non)
   - Logique de rebalancing :
     - Si `fixed_target_weights` présent : utiliser fixed weights
     - Vérification prix manquants : skip rebalance si prix manquant
     - Stockage `bundle_id` et `rebalance_mode` dans le run

5. **`api/services/backtest/repository.py`**
   - Ajout paramètres `bundle_id` et `rebalance_mode` à `create_backtest_run()`

6. **`api/services/backtest/schemas.py`**
   - `bundle_id` déjà présent dans `BacktestCreateRequest` (pas de changement)

### Tests

7. **`api/tests/test_fixed_target_weights.py`** (NOUVEAU)
   - Tests unitaires pour `compute_target_weights_fixed()`
   - Tests de validation
   - Tests de comportement de rebalancing

### Documentation

8. **`docs/AUDIT_REBALANCING.md`** (NOUVEAU)
   - Rapport d'audit complet du système existant

9. **`docs/BUNDLES_AND_BACKTESTING.md`** (NOUVEAU)
   - Documentation technique complète

### Frontend

10. **`web/src/components/backtests/BacktestBuilder.tsx`**
    - Mise à jour UI : Badge "Rebalancing: Fixed Target Weights" quand bundle sélectionné
    - Titre changé : "Bundle Allocations" → "Target Allocation"

## Comportement Implémenté

### Fixed Target Weights Mode

1. **Quand `bundle_id` est présent** :
   - `rebalance_mode` = `"fixed_target_weights"` (forcé)
   - Les target weights viennent du bundle (source de vérité)
   - À chaque rebalance : retour aux poids cibles du bundle

2. **Validation** :
   - Weights doivent sommer à 100% (tolérance 0.01)
   - **REJET** si somme != 100% (pas de normalisation automatique)

3. **Gestion prix manquants** :
   - Si un instrument du bundle n'a pas de prix open → **skip rebalance**
   - Warning ajouté : `"Skipped rebalance on {date}: missing prices for instruments {ids}"`
   - Weights inchangés, turnover = 0

4. **Entre rebalances** :
   - Weights restent inchangés (drift naturel)
   - NAV évolue selon les returns

### Strategy-Based Mode (existant)

- Si `bundle_id` = null → `rebalance_mode` = `"strategy_based"`
- Comportement inchangé : weights recalculés selon stratégie

## Migration

```bash
cd api
alembic upgrade head
```

**Migration** : `h3456789012c_add_bundle_id_to_backtest_runs`

## Tests

### Tests Unitaires

```bash
cd api
python -m pytest tests/test_fixed_target_weights.py -v
```

### Test Manuel Rapide

1. **Créer un bundle** :
   - Aller sur `/admin/bundles/new`
   - Asset Class: "crypto"
   - Nom: "Crypto 60/40"
   - Allocations: BTCUSD 60%, ETHUSD 40%
   - Sauvegarder

2. **Lancer un backtest avec bundle** :
   - Aller sur `/admin/backtests`
   - Sélectionner Asset Class: "crypto"
   - Sélectionner Bundle: "Crypto 60/40"
   - Vérifier badge "Rebalancing: Fixed Target Weights"
   - Vérifier tableau "Target Allocation" (60% / 40%)
   - Lancer backtest

3. **Vérifier résultats** :
   - Après chaque rebalance, allocation doit revenir à 60/40
   - Entre rebalances, allocation peut dériver

## Validation des Weights

### Règle : REJET si somme != 100%

**Backend** (ligne 167-169) :
```python
total_weight = sum(actual_initial_weights.values())
if abs(total_weight - 1.0) > 0.01:
    raise ValueError(f"Bundle weights do not sum to 100% (got {total_weight * 100:.2f}%)")
```

**Frontend** : Validation live dans l'éditeur de bundle (empêche sauvegarde si somme != 100%)

## Gestion des Prix Manquants

**Comportement** : SKIP REBALANCE

**Code** (lignes 284-297 de routes.py) :
```python
if missing_prices:
    warnings.append(f"Skipped rebalance on {current_date_py}: missing prices for instruments {missing_prices}")
    new_weights = prev_weights.copy()
    turnover = 0.0
```

## Points d'Attention

1. **Compatibilité** : Les backtests existants sans bundle continuent de fonctionner (mode strategy_based)
2. **Validation stricte** : Pas de normalisation automatique - l'utilisateur doit corriger
3. **Prix manquants** : Skip rebalance (pas d'erreur fatale)
4. **Source de vérité** : Les target weights viennent TOUJOURS du bundle, jamais recalculés

## Prochaines Étapes (Optionnel)

1. Tests d'intégration end-to-end
2. UI pour visualiser l'évolution de l'allocation dans le temps
3. Métriques spécifiques aux fixed weights (tracking error, etc.)

