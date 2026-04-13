# BUNDLE_ENTRY_WALLET_INVEST_FLOW_AUDIT.md

**Date** : 2026-03-22
**Objectif** : Comprendre le modèle d'investissement Bundle pour le reproduire sur les Exclusive Offer Lending Products.

---

## Executive Summary

Le système Bundle dispose d'un modèle d'investissement mature avec :
- **Entry asset configurable** (`entry_asset_default`, `entry_assets_allowed`) stocké dans les metadata du produit
- **Flow en 2 étapes** : conversion fiat→entry_asset (BUY) puis allocation entry_asset→targets (SWAPs)
- **Preview read-only** avant exécution réelle
- **Portfolio dédié** auto-provisionné par client avec positions (cash leg + spot atoms)
- **Séparation stricte** : ExchangeService (BUY/SWAP) → BundleOrchestrator (allocation) → PositionAtoms (PE)

Ce modèle peut être répliqué pour les Exclusive Offers avec une architecture simplifiée : conversion fiat/crypto → pool asset → supply to lending pool.

---

## 1. Entry Asset Model

### Stockage

| Couche | Champ | Stockage | Valeur par défaut |
|--------|-------|----------|-------------------|
| Backend (SQLAlchemy) | `entry_asset_default` | `pe_product_definitions.metadata_` (JSONB) | `"USDC"` |
| Backend (SQLAlchemy) | `entry_assets_allowed` | `pe_product_definitions.metadata_` (JSONB) | `["USDC"]` |
| Backend (Pydantic) | `BundleCreate.entry_asset_default` | Schéma de création | `"USDC"` |
| Backend (Pydantic) | `BundleCreate.entry_assets_allowed` | Schéma de création | `["USDC"]` |
| Flutter | `BundleItem.entryAssetDefault` | Champ Dart | `'USDC'` |
| Flutter | `BundleItem.entryAssetsAllowed` | Champ Dart | `['USDC']` |

### Résolution au runtime

```
api/services/portfolio_engine/bundles/orchestrator.py → _resolve_entry_config()

1. Lire ProductDefinition.metadata_
2. Extraire entry_asset_default (fallback "USDC")
3. Extraire entry_assets_allowed (fallback ["USDC"])
```

### Validation de l'asset de financement

```
_validate_funding_asset(funding_asset, entry_config)

- Si funding_asset in ["EUR", "USD"] → OK (fiat, BUY nécessaire)
- Si funding_asset in entry_assets_allowed → OK (entrée directe)
- Sinon → erreur "Funding asset X not allowed"
```

### Exposition Flutter

Le catalogue (`GET /api/app/bundle/catalog`) expose `entry_asset_default` et `entry_assets_allowed` dans chaque item. Flutter les parse dans `ProductCatalogItem` et les injecte dans `BundleItem` pour piloter le flow.

---

## 2. Bundle Invest Flow (chaîne complète)

### Vue d'ensemble

```
Flutter                          Backend
──────                          ───────
1. Sélection Bundle      →
2. Sélection Source       →     (filtre par entry_assets_allowed)
3. Saisie Montant         →     POST /bundle/invest/preview (read-only)
4. Écran Confirmation     →
5. Confirmer              →     POST /bundle/invest (exécution atomique)
                                  ├─ Step A: EUR → BUY entry_asset (USDC)
                                  ├─ Step B: Crédit cash leg portfolio
                                  ├─ Step C: Pour chaque allocation:
                                  │    ├─ SWAP entry_asset → target_asset
                                  │    ├─ Sync PE position (spot atom)
                                  │    └─ Débit cash leg
                                  └─ Return result
6. Résultat               ←
```

### Détail Flutter (5 écrans)

| Étape | Écran Flutter | Données |
|-------|--------------|---------|
| 0 | `BundleSelectionScreen` | Charge catalogue, construit `BundleItem` avec `entryAssetDefault`, `entryAssetsAllowed` |
| 1 | `BundleSourceSelectionScreen` | Affiche comptes fiat + wallets crypto filtrés par `entryAssetsAllowed` |
| 2 | `BundleAmountEntryScreen` | Saisie montant, appel preview, affiche estimation conversion |
| 3 | `BundleConfirmationScreen` | Récapitulatif montant → entry asset → allocations |
| 4 | `BundleProcessingSheet` | Appel `investInBundle()`, gestion succès/partiel/erreur |

### Détail Backend (orchestrator.py)

**Payload** :
```json
{
  "portfolio_id": "uuid",
  "funding_asset": "EUR",
  "funding_amount": 1000.0
}
```

**Étapes atomiques** :

1. **Validation** : portfolio existe, client autorisé, asset autorisé
2. **Funding** (si fiat) : `ExchangeService.buy(EUR → USDC)` → reçoit qty USDC
3. **Crédit cash leg** : `_credit_cash_leg()` → PositionAtom type=`cash` dans le portfolio
4. **Allocation** (pour chaque target) :
   - Calcul du montant pro-rata selon `target_weight`
   - `ExchangeService.swap(USDC → BTC/ETH/SOL/...)` → reçoit qty target
   - `_sync_pe_position()` → crée/met à jour PositionAtom type=`spot` dans le portfolio
   - `_debit_cash_leg()` → réduit le cash leg du montant consommé
5. **Reliquat** : cash leg restant = `entry_asset_received - sum(allocated)`

---

## 3. Preview / Confirm Flow

### Preview (read-only, aucun side-effect)

**Endpoint** : `POST /api/app/bundle/invest/preview`

**Implémentation** : `BundleOrchestrator.preview_invest()`

| Étape | Méthode | Effet |
|-------|---------|-------|
| 1 | `_exchange.preview_buy(entry_asset, fiat_amount, currency)` | Estimation qty entry_asset reçue |
| 2 | Pour chaque allocation : `_exchange.preview_swap(entry → target, amount)` | Estimation qty target reçue |
| — | Aucun order créé | Zero side-effect |

**Réponse preview** :
```json
{
  "entry_asset_used": "USDC",
  "estimated_entry_asset_amount": 985.0,
  "estimated_remaining_entry_asset": 1.2,
  "allocations": [
    {
      "asset": "BTC",
      "target_weight": 50,
      "estimated_input_amount": 492.5,
      "estimated_output_quantity": 0.0051
    }
  ]
}
```

### Confirm (exécution réelle)

**Endpoint** : `POST /api/app/bundle/invest`

Même payload que preview. Appelle `invest_into_bundle()` qui exécute les vrais BUY/SWAP via ExchangeService.

**Réponse invest** :
```json
{
  "status": "completed",
  "entry_asset": "USDC",
  "total_entry_asset_received": 985.0,
  "total_entry_asset_consumed": 983.8,
  "cash_leg_remaining": 1.2,
  "allocation_details": [
    {
      "asset": "BTC",
      "entry_asset_consumed": 492.0,
      "crypto_received": 0.00512
    }
  ]
}
```

---

## 4. Destination Wallet / Portfolio Model

### Auto-provisioning

Lors du premier appel `GET /api/app/bundle/catalog` :
1. Le système vérifie si le client a déjà un portfolio pour chaque bundle produit
2. Si non → crée automatiquement un `Portfolio` type=`bundle_portfolio` avec les `TargetAllocation` copiées du `PortfolioTemplate`

### Structure portfolio

```
Portfolio (pe_portfolios)
├── id (UUID)
├── client_id (FK → pe_clients)
├── origin_product_id (FK → pe_product_definitions)
├── portfolio_type = "bundle_portfolio"
├── name = "Top 5 Crypto"
└── TargetAllocations (pe_target_allocations)
    ├── instrument_id + target_weight (50% BTC, 30% ETH, etc.)
    └── ...

PositionAtoms (pe_position_atoms)
├── portfolio_id (FK → portfolio)
├── position_type = "spot" | "cash"
├── instrument_id (BTC, ETH, USDC)
├── quantity
└── cost_basis
```

### Lien produit → portfolio → positions

```
ProductDefinition (produit catalogue)
  ↓ origin_product_id
Portfolio (instance client)
  ↓ portfolio_id
PositionAtoms (positions réelles)
```

---

## 5. Flutter Contract (champs exposés au mobile)

### Catalogue (`GET /api/app/bundle/catalog`)

| Champ | Type | Usage |
|-------|------|-------|
| `id` | string | Product definition ID |
| `name` | string | Nom du bundle |
| `entry_asset_default` | string | Asset d'entrée par défaut (USDC) |
| `entry_assets_allowed` | string[] | Assets autorisés pour l'investissement |
| `portfolio_id` | string? | Portfolio auto-provisionné du client (null si pas encore) |
| `allocations` | object[] | Target allocations [{asset, weight}] |

### Preview result

| Champ | Type | Usage |
|-------|------|-------|
| `entry_asset_used` | string | Asset effectivement utilisé |
| `estimated_entry_asset_amount` | number | Montant estimé reçu en entry asset |
| `estimated_remaining_entry_asset` | number | Reliquat estimé |
| `allocations[].asset` | string | Target asset |
| `allocations[].estimated_output_quantity` | number | Qty estimée reçue |

### Invest result

| Champ | Type | Usage |
|-------|------|-------|
| `status` | string | completed / partial / error |
| `entry_asset` | string | Asset d'entrée utilisé |
| `total_entry_asset_received` | number | Total reçu |
| `total_entry_asset_consumed` | number | Total consommé |
| `cash_leg_remaining` | number | Reliquat |
| `allocation_details[].crypto_received` | number | Qty reçue par target |

---

## 6. Séparation des Responsabilités

```
┌─────────────────────────────────────────────────────────────┐
│                    BundleOrchestrator                        │
│  Orchestration du flow complet                              │
│  - Validation                                               │
│  - Séquençage (funding → allocation → position sync)        │
│  - Calcul des montants pro-rata                             │
│  - Gestion du cash leg                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────────┐    ┌──────────────────────┐          │
│   │  ExchangeService │    │  Portfolio Engine     │          │
│   │  - buy()         │    │  - PositionAtom       │          │
│   │  - swap()        │    │  - _sync_pe_position  │          │
│   │  - preview_buy() │    │  - _credit_cash_leg   │          │
│   │  - preview_swap()│    │  - _debit_cash_leg    │          │
│   └──────────────────┘    └──────────────────────┘          │
│                                                             │
│   ┌──────────────────┐    ┌──────────────────────┐          │
│   │  CryptoPositions │    │  Ledger              │          │
│   │  (balance réelle)│    │  (audit trail)       │          │
│   └──────────────────┘    └──────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Principes stricts** :
- L'orchestrateur ne touche JAMAIS directement les balances
- ExchangeService gère les ordres et les balances crypto
- PositionAtoms tracent les positions dans le portfolio (séparé des crypto_positions)
- Le cash leg sert de wallet intermédiaire dans le portfolio

---

## 7. Mapping vers Exclusive Offers

### Tableau de mapping conceptuel

| Concept Bundle | Où c'est géré | Comment ça marche | Mapping Exclusive Offer |
|---|---|---|---|
| `entry_asset_default` | `pe_product_definitions.metadata_` | USDC par défaut | `lending_pool.asset` (ex: USDC) |
| `entry_assets_allowed` | `pe_product_definitions.metadata_` | ["USDC"] / ["USDC","EURC"] | `lending_pool_products.metadata_` ou champ dédié → `["USDC","EUR","EURC"]` |
| Portfolio destination | `pe_portfolios` (auto-provisionné) | 1 portfolio / client / produit | `pool_supply_commitment` (pas besoin de portfolio, le pool est la destination) |
| Preview endpoint | `POST /bundle/invest/preview` | Read-only estimation | `POST /lending/products/{id}/invest/preview` (à créer) |
| Confirm endpoint | `POST /bundle/invest` | Exécution atomique | `POST /lending/products/{id}/invest` (à créer) |
| Funding step | `ExchangeService.buy(EUR → USDC)` | Conversion fiat → entry asset | Identique : `ExchangeService.buy(EUR → pool_asset)` |
| Allocation step | `ExchangeService.swap(USDC → BTC/ETH)` | Répartition multi-target | NON APPLICABLE (single asset pool) |
| Position type | PositionAtom `spot` + `cash` | Multi-asset dans portfolio | `pool_supply_commitment` + lending atom (après borrow) |
| Cash leg | PositionAtom `cash` dans portfolio | Reliquat entry asset | NON APPLICABLE (supply tout ou rien) |
| Product → Destination | `origin_product_id` → Portfolio | FK produit → portfolio | `lending_pool_products.lending_pool_id` → Pool |
| Auto-provisioning | Création portfolio au 1er accès catalogue | Transparent pour l'utilisateur | Pas nécessaire (pool existe déjà via produit) |
| Résultat | `allocation_details` par asset | Liste des trades exécutés | `commitment_id`, `amount_supplied`, `pool_id` |

### Flow Exclusive Offer proposé

```
Flutter                              Backend
──────                              ───────
1. Voir page projet           →
2. Clic "Investir"            →
3. Sélection Source            →     (comptes fiat + wallets crypto filtrés par entry_assets_allowed)
4. Saisie Montant             →     POST /lending/products/{id}/invest/preview (read-only)
5. Écran Confirmation         →     Affiche : montant → conversion → supply
6. Confirmer                  →     POST /lending/products/{id}/invest (atomique)
                                      ├─ Step A: Si fiat → BUY pool_asset (USDC)
                                      │   └─ ExchangeService.buy(EUR → USDC)
                                      ├─ Step B: Si crypto != pool_asset → SWAP
                                      │   └─ ExchangeService.swap(BTC → USDC)
                                      ├─ Step C: Supply au pool
                                      │   └─ PoolService.create_supply_commitment()
                                      ├─ Step D: Mise à jour current_raised
                                      └─ Return result
7. Résultat                   ←
```

### Différences clés Bundle vs Exclusive Offer

| Aspect | Bundle | Exclusive Offer |
|--------|--------|-----------------|
| **Nombre d'assets cibles** | N (BTC, ETH, SOL...) | 1 (pool asset, ex: USDC) |
| **SWAPs post-funding** | N swaps (entry → chaque target) | 0 ou 1 swap (entry → pool asset) |
| **Cash leg** | Oui (reliquat entry asset) | Non (supply = montant exact) |
| **Destination** | Portfolio avec positions | Pool avec commitment |
| **Positions créées** | PositionAtoms (spot + cash) | PoolSupplyCommitment (+ lending atom après borrow) |
| **Complexité** | Haute (multi-target, rebalance) | Faible (single asset, pas de rebalance) |

---

## 8. Recommendations

### 1. Réutiliser le pattern entry_asset du Bundle

Ajouter `entry_assets_allowed` dans `lending_pool_products` (colonne ou metadata JSONB) :
- Default : `[pool_asset]` (ex: `["USDC"]`)
- Extensible : `["USDC", "EUR", "EURC", "BTC"]` pour accepter d'autres assets

### 2. Créer un LendingInvestOrchestrator léger

Inspiré du `BundleOrchestrator` mais simplifié (single target) :
- Validation funding asset vs `entry_assets_allowed`
- Conversion si nécessaire (BUY ou SWAP via ExchangeService)
- Supply au pool via `PoolService.create_supply_commitment()`
- Mise à jour `current_raised` sur `LendingPoolProduct`

### 3. Endpoints preview + invest

| Endpoint | Modèle |
|----------|--------|
| `POST /api/lending/products/{id}/invest/preview` | Estimation conversion + supply amount |
| `POST /api/lending/products/{id}/invest` | Exécution atomique conversion + supply |

### 4. Flutter : répliquer le flow Bundle en 4 écrans

| Écran | Source | Adaptation |
|-------|--------|------------|
| Source selection | `BundleSourceSelectionScreen` | Filtrer par `entry_assets_allowed` du produit lending |
| Amount entry | `BundleAmountEntryScreen` | Appel preview lending, afficher estimation |
| Confirmation | `BundleConfirmationScreen` | Récapitulatif montant → conversion → supply au pool |
| Processing | `BundleProcessingSheet` | Appel invest lending, gestion résultat |

### 5. Ne PAS réutiliser le Portfolio Engine

Le lending pool a sa propre structure (`pool_supply_commitment`, `pool_allocation`, lending atoms). Pas besoin de créer un portfolio PE pour les offres exclusives.

### 6. Réutiliser ExchangeService tel quel

Le `ExchangeService.buy()` et `ExchangeService.swap()` sont les mêmes briques pour la conversion. L'orchestrateur lending les appelle de la même manière que le BundleOrchestrator.

---

## Fichiers clés de référence

| Rôle | Fichier |
|------|---------|
| Orchestrator Bundle (blueprint) | `api/services/portfolio_engine/bundles/orchestrator.py` |
| Schémas Bundle (entry_asset fields) | `api/services/portfolio_engine/bundles/schemas.py` |
| Catalogue produits | `api/services/portfolio_engine/products/catalog.py` |
| Router Bundle invest | `api/services/test_clients/router.py` |
| Pool supply service | `api/services/lending/pool_service.py` |
| Pool supply router | `api/services/lending/pool_router.py` |
| Offer product service | `api/services/lending/offer_service.py` |
| Flutter invest flow controller | `mobile/lib/.../bundle_invest_flow/bundle_invest_flow_controller.dart` |
| Flutter bundle API | `mobile/lib/features/wallet/data/bundle_api.dart` |
