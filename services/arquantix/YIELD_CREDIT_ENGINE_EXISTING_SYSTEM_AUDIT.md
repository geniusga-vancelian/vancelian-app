# YIELD & CREDIT ENGINE — Audit du système existant

> **Objectif** : Comprendre précisément l'architecture actuelle (trading, portfolio engine, custody, ledger, valuation, admin) avant d'étendre le système vers des positions de type lending, staking, borrowing, collateral et defi_lending.
>
> **Contrainte** : Aucune modification fonctionnelle. Audit seulement.

---

## Executive Summary

Le système Arquantix est aujourd'hui une **plateforme de gestion de patrimoine crypto spot + bundles** complète, avec :

- Un **Exchange Service** gérant buy/sell/swap avec WAC, PnL réalisé, et settlement
- Un **Portfolio Engine** multi-couche (direct portfolio, bundle portfolio) avec position atoms, sleeves, allocations et rebalance
- Un **Custody/Ledger** double-entry strict (fiat + crypto) avec webhooks BAS et idempotence
- Un **moteur de valuation** centralisé (USDT→EUR via FX) et un système de **performance/history**
- Un **Price Alert Engine** avec ordres auto-exécutés (limit/stop)

**Le système a été conçu avec l'extension en tête** : les enums `InstrumentType`, `PortfolioType`, `StrategyType` et les colonnes `pe_assets.supports_staking/collateral/borrowing/yield` sont déjà en place. Cependant, **toute la logique métier, valuation, performance et history suppose exclusivement du spot**. L'extension nécessitera des ajouts mesurés et progressifs, sans casser les invariants existants.

---

## 1. Entity Map

### 1.1 Trading / Exchange

| Table | Rôle | Source de vérité pour | Qui écrit | Qui lit | Criticité |
|-------|------|-----------------------|-----------|---------|-----------|
| `exchange_orders` | Journal de tous les ordres buy/sell/swap | Historique d'exécution, WAC, PnL réalisé | ExchangeService.buy/sell/swap | Wallet stats, wallet history, PnL, admin | **CRITIQUE** |
| `crypto_positions` | Solde crypto consolidé par (client, asset) | Balance spot réelle du client | ExchangeService.credit/debit | Valuation, stats, admin, Flutter | **CRITIQUE** |
| `crypto_settlement_deltas` | Deltas journaliers pour settlement externe | Rapprochement Fireblocks | ExchangeService | Settlement job, admin | HAUTE |
| `exchange_fee_config` | Config frais/spread par asset | Paramètres de pricing | Admin | ExchangeService | MOYENNE |

### 1.2 Portfolio Engine

| Table | Rôle | Source de vérité pour | Qui écrit | Qui lit | Criticité |
|-------|------|-----------------------|-----------|---------|-----------|
| `pe_clients` | Propriétaire de tous les comptes | Identité client | Provisioning | Global | **CRITIQUE** |
| `pe_portfolios` | Portefeuilles (direct/bundle/...) | Structure des portefeuilles | ensure_direct_portfolio, provisioning | Valuation, bundles, stats | **CRITIQUE** |
| `pe_position_atoms` | Positions détaillées par (portfolio, instrument) | Ventilation par portfolio | sync_direct_atom, BundleOrchestrator | Valuation, stats, drift, rebalance | **CRITIQUE** |
| `pe_instruments` | Registre des instruments tradables | Mapping asset→instrument | Auto-créés (direct_overlay, orchestrator) | Price bridge, valuations | HAUTE |
| `pe_assets` | Registre des assets sous-jacents | Métadonnées asset (supports_staking, etc.) | Auto-créés, seed | Instruments | HAUTE |
| `pe_sleeves` | Sleeves de composition (bundles) | Segmentation intra-portfolio | Provisioning | Drift, allocations | MOYENNE |
| `pe_target_allocations` | Cibles d'allocation | Poids cibles pour rebalance | Provisioning, allocations service | BundleOrchestrator, drift | HAUTE |
| `pe_portfolio_templates` | Modèles de portfolios | Templates pour provisioning | Templates service | Provisioning | MOYENNE |
| `pe_template_allocations` | Allocations par template | Poids cibles pour templates | Templates service | Provisioning | MOYENNE |
| `pe_product_definitions` | Définitions produit (bundles) | Catalogue produits | Products service | Bundle orchestrator | MOYENNE |
| `pe_product_subscriptions` | Abonnements client → produit | Lien subscription | Provisioning | Bundle service | MOYENNE |
| `pe_strategy_definitions` | Définitions de stratégies | Paramètres stratégie | Seed | Strategy instances | BASSE |
| `pe_strategy_instances` | Instances de stratégie par portfolio | Assignation stratégie | — | Strategy engine | BASSE |
| `pe_wallet_containers` | Conteneurs de wallet | Mapping custody→PE | — | Position atoms | BASSE |

### 1.3 Custody / Ledger

| Table | Rôle | Source de vérité pour | Qui écrit | Qui lit | Criticité |
|-------|------|-----------------------|-----------|---------|-----------|
| `custody_accounts` | Comptes fiat chez BAS (IBAN) | Mapping IBAN↔compte | CustodyService | Exchange, webhooks | **CRITIQUE** |
| `custody_account_balances` | Solde fiat disponible/pending | Balance EUR réelle | Webhooks, Exchange | Valuation, admin | **CRITIQUE** |
| `custody_transactions` | Mouvements fiat (dépôt, retrait, échange) | Journal fiat | Webhooks, Exchange, simulations | History, admin | **CRITIQUE** |
| `custody_providers` | Fournisseurs BAS (Modular, Zand...) | Config providers | Admin | Custody service | HAUTE |
| `custody_webhook_events` | Événements webhook bruts | Audit / idempotence | Webhook processor | Admin, replay | HAUTE |
| `crypto_custody_accounts` | Comptes techniques crypto (pool/settlement) | Un par (asset, type) | Admin, bootstrap | Exchange, settlement | HAUTE |
| `crypto_custody_balances` | Solde réel vs attendu crypto | Rapprochement Fireblocks | Admin, settlement | Admin, diagnostics | HAUTE |
| `pe_ledger_accounts` | Comptes du grand livre comptable | Comptes avec solde dérivé | Custody, Exchange | Ledger queries | **CRITIQUE** |
| `pe_ledger_entries` | Écritures comptables (append-only) | Journal immutable | LedgerEntryService.post_double_entry | Réconciliation | **CRITIQUE** |

### 1.4 Market Data / Pricing

| Table | Rôle | Source de vérité pour | Qui écrit | Qui lit | Criticité |
|-------|------|-----------------------|-----------|---------|-----------|
| `market_data_instruments` | Registre des instruments de marché | Symbol→provider mapping | Seed, admin | Quotes, price bridge | HAUTE |
| `market_data_latest_quotes` | Derniers prix (bid/ask/last) | Prix temps réel | Binance WS ingestion | Valuation, Exchange, FX | **CRITIQUE** |
| `market_data_bars_*` (1m/5m/1h/4h/1d/1w) | Historique OHLCV | Prix historiques | Binance WS ingestion | Wallet history | HAUTE |

### 1.5 Alerting / Orders

| Table | Rôle | Source de vérité pour | Qui écrit | Qui lit | Criticité |
|-------|------|-----------------------|-----------|---------|-----------|
| `price_alerts` | Alertes de prix + ordres limit/stop | Triggers actifs | API alerts/orders | PriceAlertEngine, Flutter | HAUTE |
| `notifications` | Notifications utilisateur | Historique notifs | PriceAlertEngine, dispatcher | Flutter, admin | MOYENNE |

---

## 2. Flow Map

### A. Dépôt fiat

```
BAS Webhook → WebhookProcessor.store_raw_event
           → _handle_deposit
              → CustodyTransaction.create (DEPOSIT, CREDIT)
              → CustodyBalanceRepository.update_balance (+montant)
              → LedgerEntryService.post_double_entry
              → Transaction status → COMPLETED
```

**Tables touchées** : `custody_webhook_events`, `custody_transactions`, `custody_account_balances`, `pe_ledger_entries`, `pe_ledger_accounts`

**Vues impactées** : Dashboard fiat, global statistics, global history (timeline fiat)

---

### B. Buy crypto

```
ExchangeService.buy(client, asset, fiat_amount)
  1. Idempotence check (external_reference)
  2. Fee lookup (exchange_fee_config)
  3. Balance lock (custody_account_balances FOR UPDATE)
  4. Prix résolution (market_data_latest_quotes → bid/ask)
  5. exchange_orders.create (status=processing)
  6. custody_transactions.create (EXCHANGE_BUY, DEBIT)
  7. pe_ledger_entries.post_double_entry
  8. custody_account_balances.update_balance (−fiat)
  9. crypto_positions.credit (+crypto)
  10. ensure_direct_portfolio → pe_portfolios
  11. _resolve_or_create_instrument → pe_instruments + pe_assets
  12. sync_direct_atom → pe_position_atoms (Δ qty, Δ cost_basis)
  13. crypto_settlement_deltas.increment
  14. exchange_orders.update_status → completed
  15. AuditService.log_success
```

**Tables touchées** : `exchange_orders`, `custody_transactions`, `pe_ledger_entries`, `custody_account_balances`, `crypto_positions`, `pe_portfolios`, `pe_instruments`, `pe_assets`, `pe_position_atoms`, `crypto_settlement_deltas`, `pe_audit_events`

**Balances modifiées** : EUR −fiat, crypto_positions +crypto, atom.quantity +crypto, atom.cost_basis +fiat

---

### C. Sell crypto

Flux symétrique à Buy avec :
- `crypto_positions.debit (−crypto)`
- `custody_account_balances.update_balance (+fiat)`
- WAC calculé via `get_wac_state_before_sell` → `cost_basis_consumed`, `realized_pnl_generated` persistés dans `exchange_orders`
- `sync_direct_atom` avec Δ négatif

---

### D. Swap crypto↔crypto

```
ExchangeService.swap(client, from_asset, to_asset, amount)
  = SELL from_asset (EUR temporaire) → BUY to_asset
  Deux exchange_orders liés par swap_group_id
  Deux custody_transactions (SELL debit + BUY credit)
  Atoms mis à jour pour les deux assets
```

---

### E. Invest bundle

```
BundleOrchestrator.invest_into_bundle(portfolio_id, amount, entry_asset)
  1. Charger portfolio (bundle_portfolio) + produit
  2. Financement : si EUR → BUY entry_asset (ex: USDC) via ExchangeService
  3. _credit_cash_leg → atom position_type="cash" (entry asset non alloué)
  4. Pour chaque allocation cible :
     SWAP entry_asset → target_asset
     _sync_pe_position → atom position_type="spot"
     _debit_cash_leg → réduction du cash
```

**Tables touchées** : `exchange_orders` (multiples), `crypto_positions`, `pe_position_atoms`, `custody_account_balances`, `custody_transactions`, `pe_ledger_entries`

---

### F. Rebalance bundle

```
BundleRebalanceOrchestrator.execute_rebalance(portfolio_id)
  1. Calcul drift (allocation actuelle vs cible)
  2. Phase SELL : surpondérés → SWAP asset → entry_asset
     _debit_spot_atom + _credit_cash_leg
  3. Phase BUY : sous-pondérés → SWAP entry_asset → asset
     _sync_pe_position + _debit_cash_leg
```

---

## 3. Sources of Truth

### Tableau des vérités comptables

| Question | Source de vérité primaire | Vues dérivées | Risque de divergence |
|----------|--------------------------|---------------|----------------------|
| **Balance spot d'un wallet crypto** | `crypto_positions.balance` | `pe_position_atoms.quantity` (direct + bundles) | Moyen — Invariant F vérifie direct + bundles ≈ crypto_positions |
| **Détention bundle** | `pe_position_atoms` (portfolio_type=bundle) | — | Faible — atoms mis à jour par orchestrator |
| **Vue consolidée client** | `valuation.get_portfolio_breakdown()` | Dashboard Flutter, global stats | Faible — centralisation récente |
| **Realized PnL** | `exchange_orders.cost_basis_consumed + realized_pnl_generated` | `wallet_statistics`, `pe_position_atoms.realized_pnl` | Moyen — deux sources WAC |
| **Unrealized PnL** | Calculé à la volée : `position × price − cost_basis` | `wallet_statistics`, `valuation.get_pnl()` | Faible |
| **Historique de performance** | `build_wallet_history()` reconstruit depuis `exchange_orders` + candles | Charts Flutter | Faible — reconstruction déterministe |
| **Solde fiat custody** | `custody_account_balances.available_balance` | `valuation.get_fiat_balance_eur()` | Faible — source unique |
| **Ledger / journal comptable** | `pe_ledger_entries` (append-only, double-entry) | `pe_ledger_accounts.balance` (dérivé) | Faible — immutable |

### Duplications identifiées

1. **WAC (coût moyen pondéré)** : calculé dans 3 endroits — `ExchangeOrderRepository.get_wac_state_before_sell`, `wallet_statistics`, `direct_overlay._compute_wac_price`. Risque faible car même algorithme, mais pas de source unique.

2. **Réalized PnL** : persisté dans `exchange_orders.realized_pnl_generated` ET recalculé à la volée dans `wallet_statistics`. Les deux doivent converger.

3. **Position quantity** : `crypto_positions.balance` (consolidé) vs `Σ pe_position_atoms.quantity` (ventilé). L'invariant F (`direct + bundles ≈ crypto_positions`) vérifie la cohérence.

---

## 4. Portfolio Engine Audit

### 4.1 Types de portfolio existants

| Enum value | Utilisé en production | Description |
|------------|----------------------|-------------|
| `direct_portfolio` | **OUI** | 1 par client, auto-créé au premier trade |
| `bundle_portfolio` | **OUI** | Créé par provisioning (template → subscription) |
| `yield_portfolio` | NON (prévu) | Pour positions yield-bearing |
| `single_asset_wallet` | NON | Wallet mono-asset |
| `structured_portfolio` | NON | Produits structurés |
| `managed_portfolio` | NON | Gestion déléguée |
| `advisory_portfolio` | NON | Conseil en investissement |

### 4.2 Direct Portfolio

- **Création** : `ensure_direct_portfolio(db, client_id)` — auto-provisionné au premier BUY/SELL/SWAP non-bundle
- **Nom** : "Direct Holdings"
- **Allocations** : Aucune — pas de cible, pas de rebalance
- **Atoms** : un atom `position_type="spot"` par instrument détenu
- **Mise à jour** : `sync_direct_atom(db, portfolio_id, instrument_id, qty_delta, cost_basis_delta)` — additif

### 4.3 Bundle Portfolio

- **Création** : Provisioning explicite (template → allocations → subscription → portfolio)
- **Allocations** : Cibles issues du template (`pe_target_allocations`)
- **Atoms** : `position_type="spot"` pour les crypto + `position_type="cash"` pour l'entry asset non alloué
- **Mise à jour** : `BundleOrchestrator._sync_pe_position`, `_credit_cash_leg`, `_debit_cash_leg`
- **Rebalance** : `BundleRebalanceOrchestrator`

### 4.4 Position Atoms — structure

```
pe_position_atoms
├── portfolio_id    → pe_portfolios
├── instrument_id   → pe_instruments
├── position_type   → "spot" | "cash"  (string, extensible)
├── status          → "open" | "closed"
├── quantity / available_quantity / locked_quantity
├── cost_basis / average_entry_price
├── unrealized_pnl / realized_pnl
├── accrued_income  → 0 (jamais utilisé, mais présent)
├── sleeve_id       → pe_sleeves (optionnel)
├── wallet_id       → pe_wallet_containers (optionnel)
└── strategy_instance_id → pe_strategy_instances (optionnel)
```

**Observation clé** : `accrued_income` existe déjà dans le schéma mais n'est jamais écrit. C'est un point d'ancrage naturel pour du yield futur.

### 4.5 Instruments — types prévus

| InstrumentType | Utilisé | Description |
|----------------|---------|-------------|
| `spot` | **OUI** | Positions crypto standard |
| `staking_position` | NON | Position stakée |
| `vault_share` | NON | Part de vault DeFi |
| `collateral_position` | NON | Collatéral déposé |
| `debt_liability` | NON | Emprunt |
| `yield_accrual` | NON | Accrual de rendement |
| `private_deal_share` | NON | Part de deal privé |

### 4.6 Assets — flags d'extension

```sql
pe_assets
├── supports_staking    BOOLEAN DEFAULT false
├── supports_collateral BOOLEAN DEFAULT false
├── supports_borrowing  BOOLEAN DEFAULT false
└── supports_yield      BOOLEAN DEFAULT false
```

**Tous à false aujourd'hui**, mais la structure est prête.

### 4.7 Stratégies prévues

| StrategyType | Utilisé | Description |
|--------------|---------|-------------|
| `buy_and_hold` | **OUI** (direct) | Buy & hold passif |
| `target_allocation` | **OUI** (bundles) | Allocation cible |
| `periodic_rebalance` | **OUI** (bundles) | Rebalance périodique |
| `threshold_rebalance` | NON | Rebalance sur seuil |
| `staking` | NON | Stratégie staking |
| `collateralized_borrowing` | NON | Emprunt collatéralisé |
| `cppi` | NON | CPPI |
| `core_satellite` | NON | Core-satellite |

---

## 5. Custody / Ledger Audit

### 5.1 Architecture custody fiat

```
custody_providers (Modular, Zand, ...)
  └── custody_accounts (IBAN, currency, account_type: client_deposit | settlement | ...)
        └── custody_account_balances (available_balance, pending_balance, version)
              ← custody_transactions (DEPOSIT/WITHDRAWAL/EXCHANGE_BUY/SELL, status machine)
```

**Sécurité** :
- `SELECT FOR UPDATE` + optimistic locking (`version`) sur les balances
- Machine à états stricte : `pending → processing → completed | failed | reversed`
- Idempotence : `(provider_id, external_reference)` pour transactions

### 5.2 Architecture custody crypto

```
crypto_custody_accounts (asset, account_type: clients_pool | settlement_wallet)
  └── crypto_custody_balances (actual_balance, expected_balance)
```

Rapprochement `actual` (Fireblocks réel) vs `expected` (calcul interne) pour chaque asset.

### 5.3 Ledger double-entry

```
pe_ledger_accounts (code unique, client_id, account_type, currency, balance)
pe_ledger_entries  (append-only, debit/credit, reference_type/id, counterpart_entry_id)
```

**reference_type** existants : `custody_transaction`, `exchange_order`, `settlement`, `custody_reversal`

**Propriétés** :
- **Append-only** : aucun UPDATE ni DELETE sur les entries
- **Double-entry** : chaque mouvement crée 2 entries liées par `counterpart_entry_id`
- **Extensible** : `reference_type` est un string, pas un enum SQL → on peut ajouter `lending_deposit`, `staking_reward`, etc.

### 5.4 Ce qui doit être préservé absolument

| Invariant | Description | Risque si violé |
|-----------|-------------|-----------------|
| Double-entry integrity | Chaque entry a un counterpart | Divergence comptable |
| Append-only ledger | Aucun UPDATE/DELETE sur pe_ledger_entries | Perte d'audit trail |
| Optimistic locking | Version check sur custody_account_balances | Race conditions |
| Idempotence | external_reference unique pour orders et transactions | Double exécution |
| FK cascade order | Respecter l'ordre de suppression (webhooks → tx → ledger → orders) | Violations FK |
| State machine | Transitions valides pour custody_transactions | État incohérent |

### 5.5 Réutilisabilité pour extension

| Opération future | Réutilisable ? | Comment |
|------------------|----------------|---------|
| Transfert spot → lending | **OUI** | Nouveau `transaction_kind`, ledger double-entry entre comptes spot et lending |
| Retour lending → spot | **OUI** | Même pattern, direction inverse |
| Collateral lock | **OUI** | `locked_quantity` sur atom + entry ledger |
| Internal lending/borrowing | **OUI** | Nouveaux `reference_type` ledger + comptes dédiés |
| Mouvements vers protocoles | **PARTIEL** | Nécessite nouveau handler webhook ou API protocole |

---

## 6. Performance / Valuation Audit

### 6.1 Moteur de valuation centralisé (`valuation.py`)

```python
get_portfolio_breakdown(db, client_id) → {
    fiat_value,      # custody_account_balances.available_balance
    direct_value,    # Σ atoms(direct) × prix
    bundle_value,    # Σ atoms(bundles) × prix
    crypto_total,    # crypto_positions × prix (invariant: ≈ direct + bundles)
    total_value      # fiat + crypto_total
}
```

**Pipeline de prix** : `MarketDataLatestQuote.last_price` (USDT) → `usdt_to_eur(rate)` → EUR

**FX** : `get_fx_rate(db)` → `MarketDataLatestQuote` pour EURUSDT (fallback 1.08)

### 6.2 Construction de l'historique

`build_wallet_history(db, client_id, asset, period, mode)` :

1. Charge tous les `exchange_orders` (status=completed) triés par date
2. Reconstruit les positions chronologiquement (BUY accumule, SELL consomme WAC)
3. Échantillonne via candles OHLCV pour les prix intercalaires
4. **Mode "value"** : NAV = Σ position × prix à chaque timestamp
5. **Mode "performance_value"** : PnL cumulé réalisé + latents

`build_global_history` ajoute la timeline fiat (somme cumulative des `CustodyTransaction`).

### 6.3 Calcul du PnL

| Composant | Méthode | Source |
|-----------|---------|--------|
| WAC (coût moyen) | Itération chronologique des ordres BUY | exchange_orders |
| Cost basis consumed | `qty_sold × WAC_before_sell` | Persisté dans exchange_orders |
| Realized PnL | `net_received − cost_basis_consumed` | Persisté dans exchange_orders + recalculé dans wallet_statistics |
| Unrealized PnL | `position × current_price − cost_basis` | Calculé à la volée |

### 6.4 Inventaire des hypothèses "spot only"

| Fichier | Hypothèse | Impact si extension |
|---------|-----------|---------------------|
| `wallet_history/service.py` | Reconstruction uniquement depuis `ExchangeOrder` (BUY/SELL) | **Les yield/intérêts ne seraient pas dans la timeline** |
| `wallet_statistics/service.py` L182 | `Instrument.instrument_type == "spot"` pour scope bundle | **Les positions staking/lending seraient exclues des stats** |
| `wallet_statistics/service.py` L193 | `PositionAtom.position_type == "spot"` pour scope PE | **Idem** |
| `valuations/service.py` L299 | `if position.position_type != "spot": return UNPRICED` | **Les positions non-spot ne seraient pas valorisées du tout** |
| `direct_overlay.py` | `instrument_type == "spot"` et `position_type == POSITION_TYPE_SPOT` partout | **Seul spot est synchronisé vers les atoms directs** |
| `bundles/service.py` L110-115 | "All instruments must be spot" dans la validation bundles | **Impossible d'inclure du staking/lending dans un bundle** |
| `exchange/service.py` | PnL basé uniquement sur BUY/SELL | **Aucune logique pour yield/accrual** |
| `accounting/invariants.py` | `_get_crypto_value_eur` lit uniquement `CryptoPosition` | **Positions lending/staking ne seraient pas dans le total** |
| `valuation.py` | `get_crypto_value_eur` agrège `CryptoPosition` uniquement | **Idem** |

### 6.5 Zones fragiles pour extension

1. **`build_wallet_history`** : ne connaît que BUY/SELL. Un yield accrual ne serait pas visible dans l'historique.
2. **Invariant `crypto_positions ≈ direct_atoms + bundle_atoms`** : ne tient que si toutes les positions sont spot. Un atom staking violerait cet invariant.
3. **WAC / cost_basis** : ne sait pas modéliser un gain de yield (le principal augmente sans "achat").
4. **`CryptoPosition.balance`** : ne distingue pas principal vs accrued. Si du staking augmente le solde, le WAC serait faussé.

---

## 7. Admin / Backoffice Audit

### 7.1 Capacités actuelles

| Domaine | Ce qui est monitorable | Pages admin |
|---------|------------------------|-------------|
| Custody fiat | Providers, comptes, balances, transactions, webhooks | `/admin/custody` |
| Crypto custody | Comptes (pool/settlement), actual vs expected, mismatch | `/admin/custody` |
| Exchange | Contexte (clients, balances, positions, prix), buy/sell/swap | `/admin/exchange-test` |
| Test clients | Création, sélection, suppression, preview bootstrap | `/admin/test-clients` |
| PE hardening | Rebuild positions/valuations/perf, réconciliation, scheduler | PE admin routes |
| Bundles | CRUD, visibilité, catalogue | `/admin/bundles` |
| Diagnostics | Invariants F/D/E, scope metadata, backfill | Routes diagnostics |
| Financial reset | Reset complet (transactions, orders, positions, alerts, notifications, Redis) | Bouton dans custody |

### 7.2 Ce qui manque pour lending/borrowing/staking

| Manque | Description | Priorité |
|--------|-------------|----------|
| Yield tracking | APY, récompenses, accruals par protocole/position | HAUTE |
| Statut protocole | Santé du protocole, collateral ratio, risque de liquidation | HAUTE |
| Collateral view | Positions collatéral, LTV, health factor | HAUTE |
| Emprunts actifs | Prêts, taux, échéances, remboursements | HAUTE |
| Staking view | Validateurs, unstaking period, rewards pending | HAUTE |
| Audit trail admin | Qui a fait quoi, quand (actions admin loggées) | MOYENNE |
| Alertes ops | Seuils de risque, écarts custody, indispos | MOYENNE |
| Export comptable | CSV/Excel transactions + positions pour audit/compta | BASSE |

---

## 8. Reusable Components

| Composant | Réutilisable pour extension ? | Notes |
|-----------|-------------------------------|-------|
| `pe_position_atoms` | **OUI — Point d'extension principal** | `position_type` extensible (spot, staking, lending, collateral) |
| `pe_instruments` + `InstrumentType` enum | **OUI** | Types staking/collateral/debt déjà définis |
| `pe_assets` + flags supports_* | **OUI** | Flags prêts, à activer par asset |
| `pe_portfolios` + `PortfolioType` enum | **OUI** | `yield_portfolio` déjà défini |
| `pe_ledger_entries` | **OUI** | Extensible via `reference_type` string |
| `custody_transactions` + `transaction_kind` | **OUI** | Ajout de nouveaux kinds |
| `ExchangeService` | **NON — ne pas modifier** | Dédié au trading spot, le laisser tel quel |
| `valuation.py` | **À ÉTENDRE** | Ajouter pricing des positions non-spot |
| `wallet_history` | **À ÉTENDRE** | Ajouter les événements yield dans la timeline |
| `wallet_statistics` | **À ÉTENDRE** | Élargir les filtres position_type/instrument_type |
| `crypto_positions` | **NON — garder tel quel** | Reste consolidé spot, ne pas y mélanger du lending |

---

## 9. Fragile Areas / Risks

### Risques élevés

| Zone | Risque | Mitigation |
|------|--------|------------|
| `crypto_positions.balance` | Mélanger spot + staking fausserait le WAC et le PnL | **Ne jamais écrire du non-spot dans crypto_positions** |
| Invariant F | `direct + bundles ≈ crypto_positions` casserait si des atoms non-spot apparaissent | **Exclure les atoms non-spot de l'invariant** |
| `wallet_history` reconstruction | Uniquement basé sur exchange_orders, ignore les yield events | **Ajouter une source d'événements yield** |
| `valuations/service.py` L299 | `position_type != "spot" → UNPRICED` | **Ajouter des pricing methods pour les nouveaux types** |

### Risques modérés

| Zone | Risque | Mitigation |
|------|--------|------------|
| WAC / cost_basis | Le yield augmente la quantité sans "achat" → WAC incohérent | **Définir si le yield est un "achat" à prix 0 ou un revenu séparé** |
| FX historique | Fallback à 1.08 si candle EURUSDT manquante | Améliorer le fallback |
| `accrued_income` atom | Colonne existe mais jamais écrite | Définir sémantique précise avant d'écrire |

---

## 10. Extension Recommendations

### 10.1 Hypothèses validées/invalidées

| # | Hypothèse | Verdict | Justification |
|---|-----------|---------|---------------|
| 1 | `crypto_positions` doit rester une vue consolidée spot/trading client | **✅ VALIDÉ** | C'est la source de vérité spot. Y mélanger du lending casserait le WAC, les invariants et l'Exchange Service. |
| 2 | `pe_position_atoms` est la meilleure couche pour les positions non-spot | **✅ VALIDÉ** | `position_type` est extensible, `accrued_income` est déjà prévu, les instruments non-spot sont définis. C'est le layer correct. |
| 3 | Custody/ledger actuel est réutilisable pour les futurs produits | **✅ VALIDÉ** | `reference_type` string, `transaction_kind` string, append-only, double-entry — tout est extensible sans breaking change. |
| 4 | La logique de perf suppose principalement du spot | **✅ VALIDÉ** | 8 hypothèses spot-only identifiées dans le code. L'extension nécessitera des modifications ciblées. |
| 5 | Il faut ajouter les nouveaux produits étape par étape | **✅ VALIDÉ** | Trop de couplage avec le spot. Un one-shot casserait les invariants. Phase-by-phase obligatoire. |

### 10.2 Le bon point d'extension

```
                   ┌─────────────────────────────┐
                   │     crypto_positions          │  ← NE PAS TOUCHER
                   │  (balance spot consolidée)    │     (source de vérité spot)
                   └──────────────┬────────────────┘
                                  │
         ┌────────────────────────┼─────────────────────────┐
         │                        │                         │
   ┌─────▼─────┐          ┌──────▼──────┐          ┌───────▼───────┐
   │  atoms     │          │  atoms      │          │  atoms        │
   │  direct    │          │  bundle     │          │  yield/lend   │ ← NOUVEAU
   │  spot      │          │  spot+cash  │          │  staking/etc  │
   └────────────┘          └─────────────┘          └───────────────┘
   pe_position_atoms       pe_position_atoms        pe_position_atoms
   portfolio_type=direct   portfolio_type=bundle     portfolio_type=yield
   position_type=spot      position_type=spot/cash   position_type=staking/lending/...
```

**Conclusion** : Les nouvelles positions vivent dans `pe_position_atoms` avec de nouveaux `position_type` et dans de nouveaux portfolios (`yield_portfolio`). `crypto_positions` reste inchangé.

---

## 11. Phase-by-Phase Recommended Path

### Phase 0 — Préparation (actuelle)
- ✅ Audit complet du système existant
- Définir le glossaire des nouveaux position_type
- Documenter les invariants comptables pour yield

### Phase 1 — Formaliser le spot comme type explicite
- Vérifier que tous les atoms ont `position_type="spot"` ou `"cash"` (déjà fait)
- Ajouter un invariant : `Σ atoms(spot, direct+bundle) ≈ crypto_positions`
- Ajouter la notion de "scope" aux stats et à la valuation (spot-only vs all-positions)

### Phase 2 — Lending externe simple
- Créer `InstrumentType.STAKING_POSITION` dans pe_instruments (enum déjà défini)
- Nouveau `position_type = "lending"` ou `"staking"` dans les atoms
- Nouveau `PortfolioType.YIELD_PORTFOLIO` pour isoler ces positions (enum déjà défini)
- Nouveau service `YieldService` qui écrit les atoms
- Entrées ledger avec `reference_type = "lending_deposit"` / `"lending_withdrawal"` / `"yield_accrual"`
- `custody_transactions` avec `transaction_kind = "lending_deposit"` / `"lending_withdrawal"`
- **NE PAS TOUCHER** : `ExchangeService`, `crypto_positions`, invariants spot

### Phase 3 — Valuation & performance multi-type
- Étendre `valuations/service.py` pour pricer `staking_position`, `collateral_position`
- Étendre `wallet_statistics` pour inclure les atoms non-spot dans le PnL
- Étendre `wallet_history` pour intégrer les événements yield dans la timeline
- Définir le traitement WAC : yield comme "revenue séparé" (pas d'impact sur cost_basis)

### Phase 4 — Borrowing / Collateral
- Nouveaux position_type : `"collateral"`, `"borrowing"`
- Logique de lock/unlock sur les atoms (`locked_quantity` déjà dans le schéma)
- Health factor, LTV monitoring
- Alertes de liquidation

### Phase 5 — DeFi lending
- Intégration protocoles externes (Aave, Compound, etc.)
- Webhooks ou polling pour sync des positions
- `yield_source` et `provider` dans pe_instruments

---

## Annexes — Tableaux synthétiques

### Tableau 1 : Entity Inventory

| Table | Layer | Used | Source of Truth | Extension-safe |
|-------|-------|------|-----------------|----------------|
| exchange_orders | Trading | ✅ | Ordres, WAC, PnL réalisé | ⚠️ Ne pas modifier |
| crypto_positions | Trading | ✅ | Balance spot consolidée | ⚠️ Ne pas y ajouter du non-spot |
| pe_portfolios | PE | ✅ | Structure portfolios | ✅ Nouveau type yield_portfolio |
| pe_position_atoms | PE | ✅ | Positions ventilées | ✅ **Point d'extension principal** |
| pe_instruments | PE | ✅ | Instruments | ✅ Nouveaux InstrumentType |
| pe_assets | PE | ✅ | Assets | ✅ Activer supports_* |
| custody_account_balances | Custody | ✅ | Solde fiat | ⚠️ Ne pas modifier |
| custody_transactions | Custody | ✅ | Journal fiat | ✅ Nouveau transaction_kind |
| pe_ledger_entries | Ledger | ✅ | Journal comptable | ✅ Nouveau reference_type |
| market_data_latest_quotes | Market | ✅ | Prix temps réel | ✅ Stable |
| price_alerts | Alerting | ✅ | Triggers | ✅ Indépendant |

### Tableau 2 : Current Business Flows

| Flow | Tables touchées | Balances modifiées | Vues impactées |
|------|-----------------|--------------------|----------------|
| Dépôt fiat | webhook, tx, balance, ledger | EUR + | Dashboard, global stats/history |
| Buy crypto | orders, tx, balance, ledger, position, atom, delta | EUR −, crypto + | Tout |
| Sell crypto | orders, tx, balance, ledger, position, atom, delta | EUR +, crypto − | Tout |
| Swap | 2× orders, 2× tx, position (×2), atoms (×2), delta (×2) | crypto A −, crypto B + | Tout |
| Invest bundle | N× orders, N× tx, position (×N), atoms (×N), cash_leg | EUR −, crypto + (N assets) | Bundle stats/history |
| Rebalance | N× orders, N× tx, position (×N), atoms (×N), cash_leg | Réallocation intra-bundle | Bundle stats/history |

### Tableau 3 : Safe Extension Points vs Dangerous Zones

| Zone | Sécurité | Action recommandée |
|------|----------|--------------------|
| `pe_position_atoms.position_type` | 🟢 SAFE | Ajouter staking/lending/collateral/borrowing |
| `pe_instruments.instrument_type` | 🟢 SAFE | Utiliser les InstrumentType déjà définis |
| `pe_portfolios.portfolio_type` | 🟢 SAFE | Utiliser yield_portfolio |
| `pe_assets.supports_*` | 🟢 SAFE | Activer les flags par asset |
| `pe_ledger_entries.reference_type` | 🟢 SAFE | Ajouter lending_deposit, yield_accrual, etc. |
| `custody_transactions.transaction_kind` | 🟢 SAFE | Ajouter lending_*, staking_* |
| `pe_position_atoms.accrued_income` | 🟢 SAFE | Écrire les accruals de yield |
| `pe_position_atoms.locked_quantity` | 🟢 SAFE | Utiliser pour collateral lock |
| `valuation.py` | 🟡 CAREFUL | Étendre sans casser le breakdown spot |
| `wallet_statistics` | 🟡 CAREFUL | Étendre les filtres, ne pas casser les stats spot |
| `wallet_history` | 🟡 CAREFUL | Ajouter les événements yield, ne pas modifier la reconstruction spot |
| `crypto_positions` | 🔴 DANGER | **Ne jamais y écrire du non-spot** |
| `ExchangeService` | 🔴 DANGER | **Ne pas modifier** — dédié au trading spot |
| Invariant F (direct+bundles≈positions) | 🔴 DANGER | **Ne pas y inclure les atoms non-spot** |
| `exchange_orders` WAC logic | 🔴 DANGER | **Ne pas modifier** — stabilisé et audité |

---

*Audit réalisé le 20 mars 2026 — Aucune modification fonctionnelle appliquée.*
