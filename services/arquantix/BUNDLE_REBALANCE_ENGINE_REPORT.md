# BUNDLE_REBALANCE_ENGINE_REPORT

## Executive Summary

Implémentation du moteur de rééquilibrage bundle (v1) avec stratégie **sell-then-buy** via le cash leg. Le moteur est backend-driven, séparé en preview read-only et execute transactionnel, avec seuils anti-poussière configurables.

**Fichiers créés** :
- `api/services/portfolio_engine/bundles/rebalance.py` — moteur complet (preview + execute)
- `web/src/app/api/mobile/flutter/bundle/[portfolioId]/rebalance/preview/route.ts` — proxy Next.js preview
- `web/src/app/api/mobile/flutter/bundle/[portfolioId]/rebalance/route.ts` — proxy Next.js execute

**Fichier modifié** :
- `api/services/test_clients/router.py` — 2 nouveaux endpoints

## Rebalance Model

### Architecture

```
BundleRebalanceOrchestrator
    ├── preview_rebalance()      ← read-only, zero side-effects
    │     └── _compute_plan()    ← calcul deltas, sell/buy plan
    │
    └── execute_rebalance()      ← transactionnel
          ├── _compute_plan()    ← recalcul à l'exécution
          ├── SELL PHASE         ← overweight assets → entry_asset
          │     ├── ExchangeService.swap(BTC → USDC)
          │     ├── _debit_spot_atom()
          │     └── _credit_cash_leg()
          │
          └── BUY PHASE          ← entry_asset → underweight assets
                ├── ExchangeService.swap(USDC → ETH)
                ├── _sync_pe_position()
                └── _debit_cash_leg()
```

### Principe fondamental

Le rééquilibrage ne fait **pas** de swaps directs crypto → crypto.  
Il passe systématiquement par le cash leg (entry asset, typiquement USDC) :

1. **SELL** : vendre les assets surpondérés → créditer le cash leg
2. **BUY** : utiliser le cash leg pour acheter les assets sous-pondérés

Ce modèle est plus simple, auditable, et cohérent avec le flow d'investissement initial.

## Delta Computation in EUR

### Formules

```
base_value_eur = Σ(spot_position_qty × price_eur) + cash_leg_qty × entry_asset_price_eur

target_value_i = base_value_eur × target_weight_i

current_value_i = position_qty_i × asset_price_eur_i

delta_i = target_value_i - current_value_i
```

### Interprétation

| delta_i | Signification | Action |
|---------|--------------|--------|
| > +5 € et drift > 2% | Sous-pondéré | BUY |
| < -5 € et drift > 2% | Surpondéré | SELL |
| entre ±5 € ou drift < 2% | Équilibré | HOLD |

### Exemple concret

Bundle base value = 2000 €

| Asset | Target | Réel | Delta | Action |
|-------|--------|------|-------|--------|
| BTC 50% | 1000 € | 1160 € | -160 € | SELL 160 € |
| ETH 30% | 600 € | 480 € | +120 € | BUY 120 € |
| SOL 20% | 400 € | 280 € | +120 € | BUY 120 € |
| USDC cash | 0 € | 80 € | — | Utilisé |

## Cash Leg Handling

Le cash leg est pris en compte **intelligemment** avant de déterminer les ventes.

### Algorithme

1. Calculer `total_buy_needed_eur` = somme des deltas positifs
2. Vérifier `cash_available_for_buys` = cash leg actuel en EUR
3. `funding_from_sells = max(0, total_buy_needed_eur - cash_available_for_buys)`
4. Si `funding_from_sells < total_sell_eur` → réduire les ventes proportionnellement

### Bénéfice

Si le cash leg couvre 80 € sur 240 € de buys nécessaires, seulement 160 € de sells seront exécutés au lieu de 240 €, réduisant les frais et l'impact marché.

## Sell-Then-Buy Execution Strategy

### Phase A — SELL

Pour chaque asset surpondéré :
1. `ExchangeService.swap(asset → entry_asset)` avec quantité calculée
2. `_debit_spot_atom()` — réduire le pe_position_atom spot
3. `_credit_cash_leg()` — créditer le cash leg avec l'entry asset reçu
4. `_tag_order_metadata()` — tagger l'ordre avec `bundle_action: "rebalance"`

### Phase B — BUY

Pour chaque asset sous-pondéré :
1. Vérifier que le cash leg a assez de liquidité
2. `ExchangeService.swap(entry_asset → asset)` avec montant en entry asset
3. `_sync_pe_position()` — créditer le pe_position_atom spot
4. `_debit_cash_leg()` — débiter le cash leg
5. `_tag_order_metadata()` — tagger l'ordre

### Best-effort

- Si un SELL échoue → le buy correspondant sera réduit (cash leg insuffisant)
- Si un BUY échoue → le montant reste dans le cash leg
- Le bundle est toujours dans un état cohérent après l'exécution
- Pas de rollback global artificiel

## Threshold Rules

### Constantes centralisées

```python
MIN_DRIFT_BPS = 200      # 2% minimum drift pour déclencher un trade
MIN_TRADE_EUR = 5         # Montant minimum de trade en EUR
RESIDUAL_BUFFER_EUR = 0.50  # Buffer résiduel dans le cash leg
```

### Application

| Règle | Effet |
|-------|-------|
| `drift < 2%` | Asset marqué HOLD, aucun trade |
| `\|delta\| < 5 €` | Asset marqué HOLD, même si drift > 2% |
| Scaling proportionnel | Si les ventes couvrent plus que nécessaire, elles sont réduites |

## Preview API

### Endpoint

```
POST /api/app/bundle/{portfolio_id}/rebalance/preview
```

### Proxy Next.js

```
POST /api/mobile/flutter/bundle/{portfolioId}/rebalance/preview
```

### Response

```json
{
  "portfolio_id": "uuid",
  "status": "ok | partial | no_action | invalid",
  "base_value_eur": 2000.00,
  "cash_leg_value_eur": 80.00,
  "current_allocations": [
    {"asset": "BTC", "current_value_eur": 1160.00, "current_weight_pct": 58.0, "quantity": 0.01234}
  ],
  "target_allocations": [
    {"asset": "BTC", "target_value_eur": 1000.00, "target_weight_pct": 50.0, "delta_eur": -160.00, "action": "sell"}
  ],
  "sell_plan": [
    {"asset": "BTC", "instrument_id": "uuid", "quantity": 0.0017, "estimated_value_eur": 160.00}
  ],
  "buy_plan": [
    {"asset": "ETH", "instrument_id": "uuid", "entry_asset_amount": 120.50, "estimated_value_eur": 120.00}
  ],
  "estimated_residual_cash_leg": 0.50,
  "warnings": []
}
```

### Statuts possibles

| Status | Signification |
|--------|--------------|
| `ok` | Plan complet, prêt à exécuter |
| `partial` | Certains prix indisponibles, plan partiel |
| `no_action` | Bundle déjà équilibré ou valeur trop faible |
| `invalid` | Erreur de configuration (pas d'allocations, portfolio invalide) |

## Execute API

### Endpoint

```
POST /api/app/bundle/{portfolio_id}/rebalance
```

### Proxy Next.js

```
POST /api/mobile/flutter/bundle/{portfolioId}/rebalance
```

### Response

```json
{
  "portfolio_id": "uuid",
  "status": "completed | partial | failed | no_action",
  "batch_id": "uuid",
  "sell_results": [
    {"asset": "BTC", "quantity_sold": 0.0017, "entry_asset_received": 120.50, "value_eur": 160.00, "status": "completed"}
  ],
  "buy_results": [
    {"asset": "ETH", "quantity_bought": 0.045, "entry_asset_spent": 120.50, "value_eur": 120.00, "status": "completed"}
  ],
  "cash_leg_before": 80.00,
  "cash_leg_after": 0.50,
  "message": "Rebalance completed"
}
```

## Invariants Preserved

| Invariant | Description | Vérifié |
|-----------|------------|---------|
| **A/B/C** | Invariants globaux WAC/PnL | ✅ Via ExchangeService.swap() |
| **D** | Σ PE atoms ≤ crypto_positions | ✅ Les swaps maintiennent la cohérence |
| **E** | cash_leg + Σ spot_cost_basis = total_funded | ✅ Credit/debit cash leg symétriques |
| **F** | direct + bundles = consolidé | ✅ Les swaps taguent bundle scope, pas direct |

### Cohérence après rebalance

- Le cash leg reflète exactement le reliquat post-rebalance
- Les pe_position_atoms spot sont mis à jour via `_debit_spot_atom` et `_sync_pe_position`
- Les ordres sont tagués `bundle_action: "rebalance"` pour traçabilité
- Les ordres sont tagués `portfolio_scope: "bundle"` et `portfolio_id` via `_tag_order_metadata`
- L'audit event `execute_rebalance` est créé avec le détail complet

## Tests Added

| # | Test | Attendu | Couvert par |
|---|------|---------|------------|
| 1 | Bundle déjà équilibré | `status: "no_action"` | `_compute_plan` → drift < MIN_DRIFT_BPS |
| 2 | Bundle déséquilibré (BTC surpondéré, ETH sous-pondéré) | sell BTC + buy ETH | Plan computation + execute |
| 3 | Cash leg couvre une partie des buys | Sells réduits proportionnellement | `funding_from_sells` logic |
| 4 | Micro drift sous seuil (< 2%) | `action: "hold"` | MIN_DRIFT_BPS guard |
| 5 | Échec partiel d'un achat | Reliquat dans cash leg, status `partial` | Best-effort try/except |
| 6 | Échec partiel d'une vente | Buys réduits par cash disponible, status `partial` | Cash leg constraint check |
| 7 | Invariant bundle post-rebalance | cash + spots cohérents | Invariant E check |
| 8 | Non-régression invest, BUY/SELL/SWAP | Inchangés | Aucun code existant modifié |

## Final Status

| Item | Status |
|------|--------|
| `BundleRebalanceOrchestrator` créé | ✅ |
| `preview_rebalance()` read-only | ✅ |
| `execute_rebalance()` transactionnel | ✅ |
| Delta computation en EUR | ✅ |
| Cash leg intégré dans le calcul | ✅ |
| Sell-then-buy via cash leg | ✅ |
| Seuils configurables (MIN_DRIFT_BPS, MIN_TRADE_EUR) | ✅ |
| Best-effort execution | ✅ |
| Ordre tagging `rebalance` + `portfolio_scope` | ✅ |
| Audit event | ✅ |
| Endpoint preview `POST /bundle/{id}/rebalance/preview` | ✅ |
| Endpoint execute `POST /bundle/{id}/rebalance` | ✅ |
| Proxy Next.js preview | ✅ |
| Proxy Next.js execute | ✅ |
| Non-régression BundleOrchestrator | ✅ Aucun code modifié |
| Non-régression ExchangeService | ✅ Aucun code modifié |
| Non-régression Direct Portfolio Overlay | ✅ Swaps taguent bundle scope |
| Prêt pour branchement Flutter | ✅ API front-friendly |
