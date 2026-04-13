# Audit - Système de Rebalancing Actuel

## Date: 2026-01-09

## Fichiers Clés

### Backend
1. **`api/services/backtest/engine.py`**
   - `compute_target_weights()` : Calcule les poids cibles selon la stratégie (equal_weight, momentum)
   - `apply_tradability_constraints()` : Applique les contraintes weekend
   - `compute_nav()` : Calcule la NAV du portefeuille
   - `compute_metrics()` : Calcule les métriques (CAGR, Sharpe, etc.)

2. **`api/services/backtest/routes.py`**
   - `run_backtest()` : Fonction principale qui orchestre le backtest
   - `should_rebalance()` : Détermine si on doit rebalancer à une date donnée
   - Lignes 267-290 : Logique de rebalancing dans la boucle principale

3. **`api/services/backtest/repository.py`**
   - `load_open_bars()` : Charge les prix open depuis la DB
   - `create_backtest_run()` : Crée un run de backtest

4. **`api/database.py`**
   - `BacktestRun` : Table principale des backtests
   - `Bundle` : Table des bundles (existe déjà)
   - `BundleAllocation` : Table des allocations de bundle (existe déjà avec `weight`)

## Comportement Actuel de Rebalancing

### Processus Actuel (lignes 267-290 de routes.py)

1. **À chaque date de rebalancing** :
   - Appel à `compute_target_weights()` qui **recalcule** les weights selon la stratégie
   - Pour `equal_weight` : weights = 1/n pour chaque instrument
   - Pour `momentum` : weights proportionnels aux scores de momentum
   - Les weights sont **dynamiques**, pas fixes

2. **Application des contraintes** :
   - `apply_tradability_constraints()` ajuste les weights selon les contraintes weekend
   - Normalise les weights pour que la somme = 1.0

3. **Entre les rebalances** :
   - Les weights restent inchangés (drift naturel)
   - La NAV évolue selon les returns des instruments

### Réponse à la Question Clé

**Est-ce que le rebalance conserve des target weights fixes ?**

**NON** ❌

Le système actuel :
- Recalcule les target weights à chaque rebalance selon la stratégie
- Pour les bundles : utilise les allocations comme `initial_weights` uniquement (ligne 186-189)
- Les target weights ne sont PAS fixes - ils changent selon la stratégie choisie

### Problème Identifié

**Ligne 186-189 de routes.py** :
```python
actual_initial_weights = {
    alloc.instrument_id: float(alloc.weight) / 100.0
    for alloc in allocations
}
```

Ces weights sont utilisés comme `initial_weights` (ligne 242), mais ensuite à chaque rebalance, `compute_target_weights()` est appelé et **recalcule** les weights selon la stratégie, ignorant les target weights du bundle.

## Modèle de Données Actuel

### BacktestRun
- ✅ `strategy_type` : "equal_weight" | "momentum"
- ✅ `rebalance` : "daily" | "weekly" | "monthly"
- ❌ **MANQUE** : `bundle_id` (nullable)
- ❌ **MANQUE** : `rebalance_mode` (enum: "fixed_target_weights" | "strategy_based")

### BundleAllocation
- ✅ `bundle_id` : FK vers Bundle
- ✅ `instrument_id` : FK vers MarketDataInstrument
- ✅ `weight` : Numeric(10,4) - **Déjà en pourcentage (0-100)**
- ✅ Contrainte unique (bundle_id, instrument_id)

## Conclusion

Le système actuel **ne supporte PAS** les target weights fixes. Il faut :

1. **Ajouter** `bundle_id` et `rebalance_mode` à `BacktestRun`
2. **Créer** une nouvelle fonction `compute_target_weights_fixed()` qui retourne les weights du bundle
3. **Modifier** la logique de rebalancing pour utiliser les fixed weights quand `bundle_id` est présent
4. **Valider** que les weights du bundle somment à 1.0 (ou 100%)

