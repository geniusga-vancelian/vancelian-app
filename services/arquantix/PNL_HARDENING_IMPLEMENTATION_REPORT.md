# PnL Hardening Implementation Report

## Executive Summary

Ce patch incrémental verrouille la comptabilité PnL avant l’implémentation du swap crypto ↔ crypto. Trois priorités ont été traitées :

1. **Correction du realized P&L sur les SELL** : utilisation de `amount_to` (net reçu client) au lieu de `amount_fiat` (gross)
2. **Persistance des champs** : `cost_basis_consumed` et `realized_pnl_generated` sur les ordres SELL
3. **Vérification des invariants comptables** : A, B, C via un service et un endpoint diagnostics

La méthode **Weighted Average Cost (WAC)** reste la méthode officielle, documentée et cohérente entre tous les services.

---

## Realized PnL Fix (gross vs net)

### Problème

Le realized P&L côté client utilisait `amount_fiat` (gross) au lieu de `amount_to` (net reçu). Cela surévaluait le realized de la somme des frais SELL.

**Règle métier** : `realized_pnl = net_received - cost_basis_consumed`

### Modifications

| Fichier | Changement |
|---------|------------|
| `api/services/exchange/repository.py` | `get_client_asset_sell_totals` : utilise `amount_to` (net) pour le fiat reçu ; fallback `amount_fiat - fee_amount` pour les anciens ordres sans `amount_to` |
| `api/services/wallet_statistics/service.py` | Pour les SELL, `total_sell_revenue` utilise `amount_to` (ou `amount_fiat - fee_amount` pour les anciens ordres) |
| `api/services/wallet_history/service.py` | `trade_events` enrichis avec `net_eur_sell` ; dans `_build_performance_value`, realized = `net_received - cost_basis_consumed` au lieu de `amount * (price - avg_cost)` |

### Non-régression

- Les valeurs BUY sont inchangées
- Les frais restent correctement affichés
- Les stats côté app restent cohérentes

---

## Persisted Fields Added

### Migration

- **Fichier** : `api/alembic/versions/067_add_pnl_hardening_fields.py`
- **Colonnes** : `cost_basis_consumed`, `realized_pnl_generated` sur `exchange_orders` (nullable, pour compatibilité avec les anciens ordres)

### Modèle

- **Fichier** : `api/services/exchange/models.py`
- **`ExchangeOrder`** : ajout des colonnes `cost_basis_consumed`, `realized_pnl_generated` (Numeric)

### Logique

- **Fichier** : `api/services/exchange/service.py` — méthode `sell()`
- Au moment de l’exécution SELL :
  - `get_wac_state_before_sell(client_id, asset)` : retourne `(cost_basis_total, position_qty)`
  - `avg_cost = cost_basis_total / position_qty`
  - `cost_basis_consumed = qty_sold × avg_cost`
  - `realized_pnl_generated = net_received - cost_basis_consumed`
- Ces valeurs sont persistées dans l’ordre et renvoyées dans la réponse SELL

### Réponse API

- **Fichier** : `api/services/exchange/schemas.py`
- **`ExchangeSellResponse`** : ajout de `cost_basis_consumed`, `realized_pnl_generated` (optionnels, strings)

---

## WAC Consistency

| Service | Utilisation |
|---------|-------------|
| `wallet_statistics` | `build_wallet_statistics` utilise `get_client_asset_sell_totals` (net) et `get_wac_state_before_sell` pour la cohérence |
| `wallet_history` | `_build_performance_value` utilise `net_received - cost_basis_consumed` |
| `exchange_repository` | `get_wac_state_before_sell` pour le calcul WAC au moment du SELL |

Pas de FIFO/LIFO dans ce patch. La méthode officielle = WAC.

---

## Invariant Checks

### Service

- **Fichier** : `api/services/accounting/invariants.py`
- **Fonction** : `compute_pnl_invariants(db, client_id)` → dict

**Calculs** :

- `cash_eur` : balance EUR client (custody_account_balances)
- `crypto_value` : somme des positions crypto mark-to-market (MarketDataLatestQuote)
- `nav` : cash_eur + crypto_value
- `realized_pnl`, `unrealized_pnl` : via `build_wallet_statistics` (agrégé par asset)
- `net_external_cash_flows` : deposits - withdrawals (BANK_TRANSFER_IN/OUT ou simulated deposit/withdrawal)

**Invariants** :

- **A** : `NAV == cash_eur + crypto_value` (tolérance 0.01)
- **B** : `total_pnl == realized + unrealized` (tolérance 0.01)
- **C** : `NAV == net_external_cash_flows + realized + unrealized` (tolérance 0.01)

### Endpoint

- **Route** : `GET /api/diagnostics/pnl-invariants`
- **Paramètre** : `client_id` (optionnel) — si absent, utilise le client courant (test_clients)
- **Auth** : JWT (get_current_user)

---

## Tests Added

**Fichier** : `api/tests/test_pnl_hardening.py`

| Test | Description |
|------|-------------|
| `test_pnl_buy_simple` | Buy 1000 EUR BTC ; unrealized = current_value - 1000, realized = 0 |
| `test_pnl_sell_total_with_fees` | Buy 1000 EUR BTC, sell total ; vérifier que realized utilise le net reçu |
| `test_pnl_sell_partiel` | Buy, sell 50% ; vérifier cost_basis_consumed, realized_pnl_generated, position restante |
| `test_pnl_multiple_buy_then_sell_wac` | Buy 1000+1000, sell 50% ; vérifier WAC (cost_basis_consumed = 5000) |
| `test_pnl_invariant_a` | NAV = cash + crypto |
| `test_pnl_invariant_b` | total_pnl = realized + unrealized |
| `test_pnl_invariant_c` | NAV = net_external_cash_flows + realized + unrealized |
| `test_pnl_sell_persists_cost_basis_and_realized` | L’ordre SELL persiste cost_basis_consumed et realized_pnl_generated |

---

## Non-Regression Notes

- **BUY flow** : inchangé
- **SELL flow** : inchangé (ajout des champs persistés)
- **preview_buy / preview_sell** : inchangés
- **wallet detail** : utilise `get_client_asset_sell_totals` → realized corrigé automatiquement
- **wallet statistics** : corrigé pour utiliser net
- **wallet history** : corrigé pour utiliser net
- **charts** : inchangés
- **buy/sell mobile flows** : inchangés

---

## Final Status

| Élément | Statut |
|---------|--------|
| Realized P&L (net sur SELL) | ✅ |
| Persistance cost_basis_consumed, realized_pnl_generated | ✅ |
| WAC cohérence | ✅ |
| Invariants A, B, C | ✅ |
| Endpoint diagnostics | ✅ |
| Tests (8 scénarios) | ✅ |
| Non-régression | ✅ |

**Swap crypto ↔ crypto** : non implémenté dans ce patch (hors scope).
