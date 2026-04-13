# BUNDLE PORTFOLIO ALIGNMENT AUDIT

## Executive Summary

Cet audit analyse la compatibilité du système existant (Exchange Engine, PnL/WAC, wallet_history, portfolio global) avec l'introduction d'un **Bundle Allocation Engine avancé** basé sur un wallet d'entrée (USDC / EURC).

### Verdict

Le système actuel est architecturé autour d'un modèle **1 client → 1 position par asset** (table `crypto_positions`). Ce modèle est incompatible tel quel avec des bundles qui créeraient des positions parallèles pour le même asset (ex: BTC détenu directement + BTC via bundle).

Cependant, un **Portfolio Engine (PE)** existe déjà avec un concept complet de `crypto_bundle` / `bundle_portfolio`, incluant des définitions produit, des templates d'allocation, du provisioning, du drift/rebalance et des modèles de positions segmentées (`pe_position_atoms` avec `wallet_id` et `portfolio_id`). Le PE ne dispose pas encore de bridge d'exécution vers l'Exchange Engine.

**Recommandation** : exploiter le PE existant comme couche de modélisation/orchestration et créer un bridge mince vers l'Exchange Engine pour l'exécution réelle, **sans modifier le modèle Exchange core** (`crypto_positions`, `exchange_orders`, WAC, invariants).

---

## Part 1 — Wallet Structure Audit

### Modèle actuel : `crypto_positions`

```
Table: crypto_positions
─────────────────────────────────────────────
id              UUID PK
client_id       UUID FK → pe_clients.id
asset           VARCHAR(20)
balance         NUMERIC(30,18)
available_balance NUMERIC(30,18)
created_at      TIMESTAMP
updated_at      TIMESTAMP

Contrainte: UNIQUE(client_id, asset)
```

### Constats

| Question | Réponse |
|----------|---------|
| Positions segmentables par wallet_id ? | **Non** — une position unique par `(client_id, asset)` |
| Plusieurs sources pour un même asset ? | **Non** — contrainte UNIQUE empêche BTC direct + BTC bundle |
| wallet_id / portfolio_id / strategy_id ? | **Aucun champ de ce type** |
| list_by_client filtre ? | `client_id` uniquement, tri par `asset` |
| Regroupement wallet/portfolio ? | **Inexistant** |

### Impact d'un wallet_id sur crypto_positions

Ajouter un `wallet_id` à `crypto_positions` impliquerait :

1. **Remplacement de la contrainte unique** : `(client_id, asset)` → `(client_id, asset, wallet_id)`
2. **Cascade sur tout le code Exchange** : `get_or_create_for_update(db, client_id, asset)` → ajout paramètre `wallet_id`
3. **Refonte du PnL** : le WAC serait segmenté par wallet, ce qui change les calculs realized/unrealized
4. **Impact queries existantes** : `list_by_client`, `build_wallet_statistics`, `build_wallet_history` devraient tous filtrer par wallet

**Risque** : casser la logique WAC, les invariants A/B/C, et les queries existantes.

**Recommandation** : **NE PAS modifier `crypto_positions`**. Utiliser le PE (`pe_position_atoms`) comme couche bundle, et garder `crypto_positions` comme couche "vue consolidée client".

---

## Part 2 — Exchange Engine Compatibility

### Analyse des fonctions

| Fonction | Source de fonds | Destination | wallet_id/portfolio_id ? |
|----------|----------------|-------------|--------------------------|
| `buy()` | Compte EUR client (`find_client_account`) | Position crypto `(client_id, asset)` | Non |
| `sell()` | Position crypto `(client_id, asset)` | Compte EUR client | Non |
| `swap()` | Position crypto source | Position crypto target | Non |
| `preview_sell()` | N/A | N/A | Non |
| `preview_swap()` | N/A | N/A | Non |
| `sell_all()` | Toutes positions > 0 | Compte EUR client | Non |

### Détails techniques

- **buy()** : `ExchangeBuyRequest(client_id, asset, fiat_amount, currency, external_reference)` — pas de `source_wallet_id`
- **sell()** : `ExchangeSellRequest(client_id, asset, amount_crypto, currency, external_reference)` — pas de `destination_wallet_id`
- **swap()** : `SwapRequest(from_asset, to_asset, amount_from)` — pas de paramètre wallet

### Écritures DB

Toutes les écritures (ordres, positions) sont scopées par `(client_id, asset)` sans segmentation wallet/portfolio.

### Compatibilité avec bundles

Le moteur Exchange peut être **réutilisé tel quel** comme moteur d'exécution atomique si :
- Un service de bridge traduit les ordres bundle en appels Exchange standard
- Les positions `crypto_positions` servent de **vue consolidée** (un BTC = tout le BTC du client, peu importe la source)
- La segmentation bundle/direct est gérée dans la couche PE (`pe_position_atoms`)

### Ce qu'il ne faut PAS modifier

- Logique `buy()` / `sell()` / `swap()`
- WAC dans `get_wac_state_before_sell`
- Freshness guards
- Fee computation
- Settlement logic
- Invariants A/B/C

---

## Part 3 — PnL / WAC Compatibility

### WAC actuel

Le WAC est calculé dans 3 endroits, tous avec la même logique :

1. **`get_wac_state_before_sell`** (repository.py) — état WAC avant vente
2. **`build_wallet_statistics`** (service.py) — statistiques wallet
3. **`wallet_history._build_performance_value`** (service.py) — timeseries PnL

Méthode :
```
BUY:  cost_basis += amount × price
SELL: avg_cost = cost_basis / position
      cost_consumed = amount × avg_cost
      realized_pnl = sell_revenue - cost_consumed
      cost_basis -= cost_consumed
```

### Persistance PnL

| Champ | Entité | Scope |
|-------|--------|-------|
| `cost_basis_consumed` | `ExchangeOrder` | Par ordre SELL |
| `realized_pnl_generated` | `ExchangeOrder` | Par ordre SELL |

### Scope du PnL

| Fonction | Scope | Filtrable par wallet/bundle ? |
|----------|-------|-------------------------------|
| `build_wallet_statistics(db, client_id, asset)` | Par asset | **Non** |
| `compute_pnl_invariants(db, client_id)` | Global client | **Non** |
| `get_portfolio_statistics` (router) | Global client | **Non** |

### Hypothèse critique

**Une seule position par `(client_id, asset)`** est une hypothèse fondamentale :
- `get_wac_state_before_sell` agrège tous les ordres `(client_id, asset)` sans filtre
- `build_wallet_statistics` fait de même
- La contrainte UNIQUE sur `crypto_positions` l'impose

### Impact bundle sur PnL

Si on introduit des bundles avec le même asset (BTC direct + BTC bundle) :

**Option A — Positions séparées dans crypto_positions** :
- Casse la contrainte UNIQUE
- Nécessite un WAC par wallet
- Refonte majeure de tout le PnL
- **À ÉVITER**

**Option B — crypto_positions reste consolidé, PE gère la segmentation** :
- Le WAC Exchange reste global par `(client_id, asset)`
- Le PE maintient ses propres `cost_basis` / `market_value` dans `pe_position_atoms`
- Le PnL "bundle" est calculé par le PE, pas par l'Exchange
- **RECOMMANDÉ**

### Invariants A/B/C

| Invariant | Formule | Compatible bundle ? |
|-----------|---------|---------------------|
| A | `NAV = cash_eur + crypto_value` | Oui — NAV consolidée |
| B | `total_pnl = realized + unrealized` | Oui — si on reste consolidé |
| C | `NAV = net_cash_flows + realized + unrealized` | Oui — si on reste consolidé |

Les invariants fonctionnent au niveau **client global**. Ils restent valides tant que `crypto_positions` reste la source de vérité consolidée.

---

## Part 4 — Wallet History Compatibility

### API actuelle

```
GET /api/app/wallet/history
  ?period=1D|1W|1M|ALL
  &asset=BTC (optionnel — un seul asset)
  &mode=value|performance_value
  &scope=crypto (accepté mais non utilisé)
```

### Fonction `build_wallet_history`

```python
def build_wallet_history(
    db: Session,
    client_id,
    reference_currency: str = "EUR",
    asset: Optional[str] = None,   # un seul asset ou tous
    mode: str = "value",
) -> dict:
```

### Filtres disponibles

| Filtre | Supporté | Commentaire |
|--------|----------|-------------|
| Un seul asset | **Oui** | `asset=BTC` |
| Multi-assets (subset) | **Non** | Pas de paramètre `assets: list[str]` |
| wallet_id / portfolio_id | **Non** | Pas de paramètre |
| scope=crypto | **Non fonctionnel** | Accepté par l'API mais ignoré par le service |

### Compatibilité bundle

Pour construire une courbe de performance pour un bundle :

**Option A — Ajouter paramètre `assets: list[str]`** :
- Filtrer les ordres par `asset IN (assets)`
- Filtrer les candles par subset d'instruments
- Impact modéré — modification d'une seule fonction
- **RECOMMANDÉ comme étape 1**

**Option B — Ajouter paramètre `portfolio_id`** :
- Plus complexe — nécessite mapping PE → Exchange orders
- Utile si un même asset est dans plusieurs bundles
- **Étape 2 si nécessaire**

### Reconstruction quantity_t

La reconstruction des positions est faite par replay chronologique des `ExchangeOrder` :
```python
for each trade event:
    if BUY: positions[asset] += amount
    if SELL: positions[asset] -= amount
```

Ceci reste correct pour un bundle si les ordres bundle sont marqués (ex: `metadata_` ou futur `bundle_id` sur `ExchangeOrder`).

---

## Part 5 — Portfolio Aggregation Impact

### Architecture actuelle

Le portfolio global ("Mes crypto") est une **simple agrégation** :
- `CryptoPositionRepository.list_by_client(db, client.id)` → toutes les positions
- Somme des `current_value`, `realized_pnl`, `unrealized_pnl`
- Pas d'entité "portfolio" explicite dans le module Exchange

### Risque de double comptage

Si un bundle utilise l'Exchange Engine pour acheter du BTC :
- L'achat est enregistré dans `crypto_positions(client_id, BTC)` — position consolidée
- Le portfolio global "Mes crypto" comptabilise ce BTC
- Le bundle PE comptabilise aussi ce BTC via `pe_position_atoms`

**Pas de double comptage dans `crypto_positions`** car c'est la source de vérité consolidée.
**Double comptage possible dans l'UI** si on affiche séparément "All Crypto" et "Bundle" sans soustraire.

### Recommandation

| Approche | Description | Complexité |
|----------|-------------|------------|
| **A — Bundle inclus dans All Crypto** | All Crypto = tout, Bundle = sous-vue | Faible — pas de soustraction |
| **B — Bundle séparé de All Crypto** | All Crypto = direct only, Bundle = bundle only | Élevée — nécessite marquage des ordres |
| **C — Affichage hiérarchique** | All Crypto = total, avec breakdown direct vs bundle | Modérée |

**Recommandation** : **Option A** pour V1, avec un label "dont X€ via bundles" si nécessaire.

---

## Part 6 — Data Model Analysis

### Tables existantes pertinentes

#### Module Exchange (actif, en production)

| Table | Rôle | wallet/portfolio_id ? |
|-------|------|----------------------|
| `crypto_positions` | Positions client consolidées | **Non** |
| `exchange_orders` | Ordres buy/sell/swap | **Non** |
| `exchange_fee_config` | Configuration frais | N/A |
| `crypto_settlement_deltas` | Règlements | N/A |

#### Module PE (existant, partiellement utilisé)

| Table | Rôle | wallet/portfolio_id ? |
|-------|------|----------------------|
| `pe_portfolios` | Portfolios client | Oui — `client_id`, `portfolio_type` (`bundle_portfolio`) |
| `pe_position_atoms` | Positions segmentées | Oui — `portfolio_id`, `wallet_id`, `instrument_id` |
| `pe_wallet_containers` | Conteneurs wallet | Oui — `portfolio_id`, `client_id` |
| `pe_orders` | Ordres PE | Oui — `portfolio_id`, `client_id` |
| `pe_trades` | Trades PE | Via `order_id` |
| `pe_ledger_accounts` | Comptes de grand livre | `wallet_container_id` |
| `pe_ledger_entries` | Écritures comptables | `account_id` |
| `pe_product_definitions` | Définitions produit (`crypto_bundle`) | N/A |
| `pe_portfolio_templates` | Templates d'allocation | `product_id` |
| `pe_template_allocations` | Allocations cibles | `template_id`, `instrument_id` |
| `pe_target_allocations` | Allocations cibles par portfolio | `portfolio_id` |
| `pe_strategy_definitions` | Définitions de stratégie | N/A |
| `pe_strategy_instances` | Instances par portfolio | `portfolio_id` |
| `pe_rebalance_policies` | Politiques de rebalance | `portfolio_id` |
| `pe_rebalance_previews` | Plans de rebalance | `portfolio_id` |

#### Tables bundles existantes

| Table | Rôle | Usage actuel |
|-------|------|--------------|
| `bundles` | Bundles market data / backtest | Backtest uniquement |
| `bundle_allocations` | Allocations de bundles | Backtest uniquement |
| `market_data_bundles` | Bundles avec JSON instrument_ids | Market data |

### Concept existant dans le PE

Le PE a déjà :
- `ProductType.CRYPTO_BUNDLE = "crypto_bundle"`
- `PortfolioType.BUNDLE_PORTFOLIO = "bundle_portfolio"`
- Provisioning : `Subscription → Portfolio + TargetAllocations + RebalancePolicy`
- Drift/rebalance : `DriftRebalanceService` calcule les écarts et génère des plans

### Contraintes existantes

| Table | Contrainte | Impact bundle |
|-------|-----------|---------------|
| `crypto_positions` | `UNIQUE(client_id, asset)` | **Bloquante si on veut plusieurs positions par asset** |
| `pe_position_atoms` | `UNIQUE(portfolio_id, instrument_id) WHERE status='open'` | OK — une position par portfolio par instrument |

---

## Part 7 — Gap Analysis

### ✅ Ce qui est déjà prêt

| Composant | État | Fichier(s) |
|-----------|------|------------|
| Exchange Engine (buy/sell/swap) | Production | `exchange/service.py` |
| WAC / PnL réalisé | Production | `exchange/repository.py`, `wallet_statistics/service.py` |
| Pricing live (bid/ask + freshness) | Production | `exchange/service.py` |
| Fee computation | Production | `exchange/service.py` |
| Invariants A/B/C | Production | `accounting/invariants.py` |
| wallet_history / timeseries | Production | `wallet_history/service.py` |
| wallet_statistics | Production | `wallet_statistics/service.py` |
| Portfolio Statistics (All Crypto) | Production | `test_clients/router.py` |
| Bundle definition (ProductDefinition) | Existant | `portfolio_engine/products/` |
| Bundle templates + allocations | Existant | `portfolio_engine/templates/` |
| Provisioning (Subscription → Portfolio) | Existant | `portfolio_engine/provisioning/` |
| Drift / rebalance (calcul + preview) | Existant | `portfolio_engine/drift/`, `rebalancing/` |
| Position atoms avec wallet_id | Existant | `portfolio_engine/positions/` |
| WalletContainer | Existant | `portfolio_engine/wallets/` |

### ❌ Ce qui manque

| Composant | Description | Priorité |
|-----------|-------------|----------|
| **Bridge PE → Exchange** | Service qui transforme un plan de rebalance en appels `buy()`/`sell()` | **P0** |
| **Bundle cash management** | Gestion du cash USDC/EURC dédié au bundle (dépôt, suivi, retraits) | **P0** |
| **Mapping instrument ↔ asset** | Lien stable entre `pe_instruments.id` et le symbole `asset` (BTC, ETH) | **P0** |
| **Sync PE ↔ Exchange positions** | Mise à jour de `pe_position_atoms` après exécution Exchange | **P0** |
| **Scheduler de rebalance** | Job périodique basé sur `RebalancePolicy` | **P1** |
| **Bundle PnL calculator** | PnL dédié au bundle (via `pe_position_atoms.cost_basis` + market_value) | **P1** |
| **Bundle timeseries** | Courbe de performance par bundle (filtre multi-assets ou portfolio_id) | **P1** |
| **Bundle statistics API** | Endpoint pour stats bundle (valeur, PnL, allocation courante) | **P1** |
| **Flutter bundle screens** | UI de souscription, suivi, performance, allocation | **P2** |
| **Retry / error handling** | Gestion des échecs d'exécution dans le bridge | **P1** |

### 🔧 Ce qui doit être modifié (impact minimal)

| Composant | Modification | Impact |
|-----------|-------------|--------|
| `exchange_orders.metadata_` | Ajouter `bundle_id` / `portfolio_id` dans le JSONB | **Nul** — champ JSONB existant |
| `wallet_history.build_wallet_history` | Ajouter paramètre `assets: list[str]` optionnel | **Faible** — modification locale |
| `portfolio/statistics` API | Ajouter breakdown "direct vs bundle" | **Faible** |
| Provisioning PE | Créer `WalletContainer` + initial `PositionAtoms` | **Faible** — extension du flux existant |

### 🚫 Ce qu'il ne faut surtout PAS toucher

| Composant | Raison |
|-----------|--------|
| `crypto_positions` schema | Casser la contrainte UNIQUE casserait WAC, PnL, invariants |
| `exchange_orders` schema (colonnes) | Ajout de FK complexifie les migrations |
| Logique WAC dans `get_wac_state_before_sell` | La mécanique est validée et testée |
| `buy()` / `sell()` / `swap()` core | Moteur validé, pas de paramètre wallet à injecter |
| Invariants A/B/C | Restent au niveau client global |
| Fee computation | Indépendante de la notion de bundle |
| Freshness guards | Indépendantes de la notion de bundle |

---

## Part 8 — Recommended Architecture

### Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                     FLUTTER / NEXT.JS                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ All Crypto │  │  Bundle    │  │  Bundle Stats /        │ │
│  │  (direct)  │  │  Detail    │  │  Performance           │ │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬─────────────┘ │
└────────┼───────────────┼────────────────────┼────────────────┘
         │               │                    │
    ┌────┼───────────────┼────────────────────┼────────────────┐
    │    │          API Layer                  │                │
    │    │               │                    │                │
    │ GET /portfolio/ GET /bundles/        GET /bundles/       │
    │ statistics     {id}/detail          {id}/statistics     │
    │                    │                    │                │
    └────┼───────────────┼────────────────────┼────────────────┘
         │               │                    │
    ┌────┼───────────────┼────────────────────┼────────────────┐
    │    │          Service Layer              │                │
    │    │               │                    │                │
    │    │    ┌──────────┴──────────┐         │                │
    │    │    │  Bundle Allocation  │    ┌────┴──────────┐     │
    │    │    │  Orchestrator       │    │ Bundle Stats  │     │
    │    │    │                     │    │ Service       │     │
    │    │    │  1. Read target     │    │               │     │
    │    │    │     allocations     │    │ PnL from PE   │     │
    │    │    │  2. Compute drift   │    │ position_atoms│     │
    │    │    │  3. Generate plan   │    │               │     │
    │    │    │  4. Execute via     │    └───────────────┘     │
    │    │    │     Exchange bridge │                          │
    │    │    │  5. Sync PE atoms   │                          │
    │    │    └──────────┬──────────┘                          │
    │    │               │                                     │
    │    │    ┌──────────┴──────────┐                          │
    │    │    │  Exchange Bridge    │                          │
    │    │    │                     │                          │
    │    │    │  PE plan → Exchange │                          │
    │    │    │  buy()/sell() calls │                          │
    │    │    └──────────┬──────────┘                          │
    │    │               │                                     │
    │    │    ┌──────────┴──────────────────────────────┐      │
    │    │    │         Exchange Engine (INCHANGÉ)      │      │
    │    │    │                                         │      │
    │    │    │  buy() → crypto_positions + EUR custody │      │
    │    │    │  sell() → crypto_positions + EUR custody│      │
    │    │    │  swap() → crypto_positions              │      │
    │    │    │                                         │      │
    │    │    │  WAC / PnL / Invariants — UNTOUCHED     │      │
    │    │    └─────────────────────────────────────────┘      │
    │    │                                                     │
    └────┼─────────────────────────────────────────────────────┘
         │
    ┌────┼─────────────────────────────────────────────────────┐
    │    │          Data Layer                                  │
    │    │                                                     │
    │    │  ┌─────────────────┐    ┌─────────────────────────┐ │
    │    │  │ crypto_positions│    │ pe_position_atoms       │ │
    │    │  │ (consolidated)  │    │ (per portfolio/wallet)  │ │
    │    │  │                 │    │                         │ │
    │    │  │ BTC: 0.5        │    │ Bundle1/BTC: 0.3        │ │
    │    │  │ ETH: 2.0        │    │ Bundle1/ETH: 1.0        │ │
    │    │  │                 │    │ Direct/BTC: 0.2          │ │
    │    │  │                 │    │ Direct/ETH: 1.0          │ │
    │    │  └─────────────────┘    └─────────────────────────┘ │
    │    │                                                     │
    │    │  ┌─────────────────┐    ┌─────────────────────────┐ │
    │    │  │ exchange_orders │    │ pe_target_allocations   │ │
    │    │  │ (all trades)    │    │ (bundle allocation %)   │ │
    │    │  │ metadata_: {    │    │                         │ │
    │    │  │   bundle_id:... │    │ BTC: 60%                │ │
    │    │  │ }               │    │ ETH: 40%                │ │
    │    │  └─────────────────┘    └─────────────────────────┘ │
    └──────────────────────────────────────────────────────────┘
```

### Flux d'exécution d'un bundle

#### 1. Souscription

```
Client → Subscribe(product_id, amount_usdc)
  → ProductSubscription created
  → Provisioning:
    → Portfolio (type=bundle_portfolio)
    → TargetAllocations (60% BTC, 40% ETH)
    → RebalancePolicy (monthly)
    → WalletContainer(s)
```

#### 2. Allocation initiale

```
BundleOrchestrator.allocate(portfolio_id, amount_usdc):
  1. Read target_allocations → [{BTC: 60%}, {ETH: 40%}]
  2. Convert USDC → EUR (si nécessaire)
  3. Compute amounts: BTC = 600€, ETH = 400€
  4. For each allocation:
     a. Exchange.buy(client_id, asset=BTC, fiat_amount=600, currency=EUR,
                     external_reference=f"bundle-{portfolio_id}-BTC-init")
        → exchange_orders.metadata_ = {"bundle_id": portfolio_id}
     b. Update pe_position_atoms:
        → quantity += amount_crypto_received
        → cost_basis += fiat_amount
  5. Audit event: bundle_allocation_completed
```

#### 3. Rebalance périodique

```
BundleOrchestrator.rebalance(portfolio_id):
  1. Read pe_position_atoms (current quantities)
  2. Value positions (market_data latest quotes)
  3. Compute current weights vs target weights
  4. DriftRebalanceService → rebalance plan (sell overweight, buy underweight)
  5. For each sell:
     Exchange.sell(client_id, asset, amount_crypto)
     Update pe_position_atoms (quantity -= sold)
  6. For each buy:
     Exchange.buy(client_id, asset, fiat_amount)
     Update pe_position_atoms (quantity += bought)
  7. Audit: rebalance_completed
```

### Données bundle dans exchange_orders

Pas besoin d'ajouter une colonne. Utiliser le champ JSONB existant `metadata_` :

```json
{
  "bundle_id": "uuid-portfolio-id",
  "bundle_action": "initial_allocation | rebalance | withdrawal",
  "rebalance_run_id": "uuid"
}
```

Cela permet de :
- Filtrer les ordres bundle pour le PnL bundle
- Garder la compatibilité avec le schéma existant
- Éviter une migration destructive

### PnL bundle

Le PnL bundle est calculé à partir de `pe_position_atoms` :

```
bundle_cost_basis = Σ pe_position_atoms.cost_basis (pour le portfolio)
bundle_market_value = Σ quantity × latest_price
bundle_unrealized = bundle_market_value - bundle_cost_basis
bundle_realized = Σ exchange_orders.realized_pnl_generated
                  WHERE metadata_->>'bundle_id' = portfolio_id
```

### Timeseries bundle

Deux approches :

1. **V1** : `build_wallet_history` avec nouveau paramètre `assets: list[str]` + filtre orders par `metadata_->>'bundle_id'`
2. **V2** : Service dédié `build_bundle_history(db, portfolio_id)` utilisant `pe_position_atoms` + market data

---

## Part 9 — Risks

### Risques identifiés

| # | Risque | Probabilité | Impact | Mitigation |
|---|--------|-------------|--------|------------|
| 1 | **Mélange PnL bundle / global** | Moyenne | Élevé | PnL bundle via PE (`pe_position_atoms`), PnL global via Exchange (`crypto_positions`) — deux sources séparées |
| 2 | **Double comptage UI** | Élevée | Moyen | Convention claire : All Crypto = consolidé (inclut bundles), Bundle = sous-vue |
| 3 | **Sync PE ↔ Exchange positions** | Moyenne | Élevé | Sync après chaque exécution Exchange + réconciliation périodique |
| 4 | **Drift entre PE atoms et crypto_positions** | Moyenne | Élevé | Vérification d'invariant : Σ pe_atoms par asset = crypto_positions.balance |
| 5 | **Complexité queries JSONB** | Faible | Faible | Index GIN sur `metadata_` si besoin, ou colonne `bundle_id` nullable ultérieurement |
| 6 | **Performance queries** | Faible | Moyen | Index sur `exchange_orders.metadata_` si filtre JSONB fréquent |
| 7 | **Migration DB** | Faible | Faible | Pas de migration destructive — uniquement ajouts (index, données PE) |
| 8 | **Échec partiel d'allocation** | Moyenne | Élevé | Stratégie best-effort + retry + audit trail (pattern sell_all existant) |
| 9 | **Cohérence WAC multi-bundle** | Faible | Élevé | Le WAC Exchange reste global par (client, asset) — le WAC bundle est calculé séparément dans PE |
| 10 | **Rebalance concurrent** | Moyenne | Élevé | Lock sur portfolio_id avant rebalance (pattern SELECT FOR UPDATE) |

### Risque principal

Le risque #3 (sync PE ↔ Exchange) est le plus critique. Si `pe_position_atoms` et `crypto_positions` divergent, le PnL bundle sera faux.

**Mitigation** : exécuter la sync dans la même transaction que l'appel Exchange, ou immédiatement après avec vérification.

---

## Final Recommendation

### Stratégie recommandée : "PE as Overlay"

1. **`crypto_positions` reste la source de vérité consolidée** — INCHANGÉ
2. **`pe_position_atoms` sert de couche de segmentation** — qui possède quoi dans quel bundle
3. **`exchange_orders.metadata_` porte le `bundle_id`** — sans migration de schéma
4. **Un service `BundleOrchestrator`** fait le pont entre PE (allocations, drift) et Exchange (exécution)
5. **Le PnL bundle est calculé par le PE** (cost_basis + market_value dans `pe_position_atoms`)
6. **Le PnL global reste calculé par l'Exchange** (WAC sur `exchange_orders`)

### Phases de mise en œuvre

| Phase | Contenu | Effort |
|-------|---------|--------|
| **Phase 1** | Bridge PE → Exchange + allocation initiale | 2-3 jours |
| **Phase 2** | Bundle stats API + PnL bundle | 1-2 jours |
| **Phase 3** | Rebalance engine (drift → plan → execution) | 2-3 jours |
| **Phase 4** | Flutter bundle screens (souscription, suivi, performance) | 3-5 jours |
| **Phase 5** | Scheduler + retry + monitoring | 1-2 jours |

### Invariants à maintenir

- **Invariant A** : `NAV = cash_eur + crypto_value` — reste au niveau client global
- **Invariant B** : `total_pnl = realized + unrealized` — reste au niveau client global
- **Invariant C** : `NAV = net_cash_flows + realized + unrealized` — reste au niveau client global
- **Nouvel invariant D** : `Σ pe_position_atoms.quantity (par asset) ≤ crypto_positions.balance` — vérification de cohérence PE ↔ Exchange

### Conclusion

Le système existant est **bien préparé** pour un bundle avancé grâce au PE existant. La stratégie "PE as Overlay" permet d'introduire les bundles **sans modifier le moteur Exchange core**, en exploitant les modèles PE déjà en place (`pe_portfolios`, `pe_position_atoms`, `pe_target_allocations`, drift/rebalance) et en construisant un bridge d'exécution mince.
