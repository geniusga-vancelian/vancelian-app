# Swap Crypto ↔ Crypto Implementation Report

## Executive Summary

Le swap crypto ↔ crypto a été implémenté de manière comptablement rigoureuse. Un swap BTC → ETH est traité comme :
1. **SELL BTC** dans la devise de référence (EUR) → `net_reference_value`
2. **BUY ETH** avec exactement `net_reference_value` comme cost basis

Une seule valeur de référence EUR par swap. Pas de perte invisible, invariants préservés.

---

## Accounting Model

### Étape 1 — SELL source asset

- `source_asset_quantity_sold` = amount_from
- `source_execution_price_in_ref_ccy` = bid (via `_resolve_price(..., side="sell")`)
- `gross_reference_value` = quantity × price
- `fee_in_reference_currency` = gross × fee_bps / 10000
- `net_reference_value` = gross - fee

Puis :
- `cost_basis_consumed_source` = quantity_sold × avg_cost_source (WAC)
- `realized_pnl_generated_source` = net_reference_value - cost_basis_consumed_source

### Étape 2 — BUY target asset

- Utilisation exacte de `net_reference_value` comme valeur d’achat
- `target_asset_quantity_bought` = net_reference_value / target_execution_price_in_ref_ccy
- `cost_basis_target_added` = net_reference_value

**Aucun mouvement EUR** : pas de custody transaction, pas de ledger EUR. Seules les positions crypto et les settlement deltas sont mis à jour.

---

## Reference Value Rule

- **Une seule référence EUR** par swap
- La jambe BUY consomme exactement la valeur nette issue de la jambe SELL
- Interdiction : SELL avec valeur A, BUY avec valeur B recalculée indépendamment

---

## Data Model / Persistence

### Migration 068

- Colonne `swap_group_id` (UUID, nullable) sur `exchange_orders`
- Index `ix_exchange_orders_swap_group_id`

### Deux ordres liés

- **SELL leg** : `side="sell"`, `asset=from_asset`, `to_asset=to_asset`, `amount_to=net_reference_value`, `cost_basis_consumed`, `realized_pnl_generated`, `swap_group_id`
- **BUY leg** : `side="buy"`, `asset=to_asset`, `amount_fiat=net_reference_value` (cost basis), `swap_group_id`

### Champs persistés

| Champ | SELL leg | BUY leg |
|-------|----------|---------|
| swap_group_id | ✓ | ✓ |
| cost_basis_consumed | ✓ | - |
| realized_pnl_generated | ✓ | - |
| amount_to | net_reference_value | target_quantity |
| amount_fiat | gross | net_reference_value |
| metadata_.swap_leg | "sell" | "buy" |
| metadata_.reference_value_net | ✓ | ✓ |

---

## Preview API

**POST /api/app/exchange/swap/preview**

Request :
```json
{
  "from_asset": "BTC",
  "to_asset": "ETH",
  "amount_from": 0.01
}
```

Response :
```json
{
  "from_asset": "BTC",
  "to_asset": "ETH",
  "amount_from": 0.01,
  "estimated_reference_value_gross": 980.00,
  "fee_in_reference_currency": 4.90,
  "estimated_reference_value_net": 975.10,
  "estimated_to_amount": 0.42,
  "from_price_in_ref_ccy": 98000.0,
  "to_price_in_ref_ccy": 2321.0,
  "reference_currency": "EUR",
  "is_fresh": true
}
```

---

## Execution API

**POST /api/app/exchange/swap**

Request :
```json
{
  "from_asset": "BTC",
  "to_asset": "ETH",
  "amount_from": 0.01
}
```

Le backend génère un `external_reference` unique pour l’idempotence.

Response (succès) :
```json
{
  "status": "completed",
  "swap_group_id": "...",
  "sell_order_id": "...",
  "buy_order_id": "...",
  "from_asset": "BTC",
  "to_asset": "ETH",
  "amount_from": 0.01,
  "amount_to": 0.42,
  "reference_value_gross": 980.00,
  "fee_in_reference_currency": 4.90,
  "reference_value_net": 975.10,
  "cost_basis_consumed": "850.00",
  "realized_pnl_generated": "125.10",
  "from_position_after": 0.01,
  "to_position_after": 0.42
}
```

---

## WAC / Realized Handling

- **Source (SELL)** : `get_wac_state_before_sell` → avg_cost → `cost_basis_consumed` = qty × avg_cost, `realized_pnl` = net - cost_basis_consumed
- **Target (BUY)** : `amount_fiat` = net_reference_value → cost basis correct pour WAC
- `wallet_statistics` et `wallet_history` utilisent les ordres existants ; les swap legs sont des ordres normaux (sell/buy) et sont pris en compte automatiquement

---

## Invariant Preservation

- **Invariant A** : NAV = cash_eur + crypto_value ✓
- **Invariant B** : total_pnl = realized + unrealized ✓
- **Invariant C** : NAV = net_external_cash_flows + realized + unrealized ✓

Le swap ne crée ni ne détruit de richesse ; il transforme une exposition crypto en une autre. Les tests vérifient ces invariants après swap.

---

## Tests Added

| Test | Description |
|------|-------------|
| test_swap_simple_btc_to_eth | Asset source réduit, target augmente, realized/cost basis corrects |
| test_swap_with_fees | Valeur nette du SELL = base du BUY, pas d’euro fantôme |
| test_swap_preserves_invariants | Invariants A/B/C après swap |
| test_swap_insufficient_source_balance | Swap rejeté si balance source insuffisante |
| test_swap_multiple_sequential | BTC→ETH puis ETH→SOL, cohérence des cost basis |
| test_swap_preview_vs_execution | Preview cohérente avec exécution |

Test 5 (quote stale) : non implémenté (nécessiterait de mocker `quote_time`).

---

## Non-Regression Notes

- BUY flow : inchangé
- SELL flow : inchangé
- wallet history : inchangé (les swap legs apparaissent comme ordres)
- wallet statistics : inchangé (WAC inclut les swap legs)
- all crypto, charts, buy/sell flows mobile : inchangés
- Invariants PnL : préservés

---

## Final Status

| Élément | Statut |
|---------|--------|
| Modèle comptable (SELL + BUY, référence unique) | ✅ |
| swap_group_id + migration | ✅ |
| preview_swap | ✅ |
| swap (exécution) | ✅ |
| Pricing (bid source, ask target) | ✅ |
| WAC / realized | ✅ |
| Invariants A/B/C | ✅ |
| Tests (6 scénarios) | ✅ |
| Non-régression | ✅ |
