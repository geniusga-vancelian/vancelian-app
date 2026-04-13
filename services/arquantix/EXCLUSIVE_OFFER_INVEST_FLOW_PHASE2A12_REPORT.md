# EXCLUSIVE_OFFER_INVEST_FLOW_PHASE2A12_REPORT.md

**Date** : 2026-03-22
**Phase** : 2A.12 — Exclusive Offer Invest Flow (Bundle-style Entry Wallet)

---

## Executive Summary

Implémentation du flow d'investissement pour les Exclusive Offer Lending Products, en reprenant le pattern du Bundle : **entry asset configurable → preview read-only → invest atomique → supply au pool**.

Le système permet à un client d'investir dans une offre exclusive depuis n'importe quel asset autorisé (EUR, BTC, USDC…), avec conversion automatique vers le pool asset si nécessaire.

---

## 1. Entry Asset Model

### Nouvelles colonnes sur `lending_pool_products`

| Colonne | Type | Description |
|---------|------|-------------|
| `entry_asset_default` | `VARCHAR(20)` | Asset d'entrée par défaut (= pool asset si non spécifié) |
| `entry_assets_allowed` | `JSONB` | Liste des assets autorisés pour l'investissement |

### Résolution au runtime

```
pool_asset = product.asset (ex: USDC)
entry_asset_default = product.entry_asset_default || pool_asset
entry_assets_allowed = product.entry_assets_allowed || [entry_asset_default]
```

### Validation du funding asset

| Source | Type | Accepté ? |
|--------|------|-----------|
| EUR, USD, CHF, GBP | Fiat | Toujours (→ buy) |
| USDC (= pool asset) | Crypto direct | Toujours (→ pas de conversion) |
| BTC, ETH… | Crypto différent | Si dans `entry_assets_allowed` (→ swap) |
| SOL (non autorisé) | — | Rejeté avec `FundingAssetNotAllowedError` |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                LendingInvestOrchestrator                     │
│  Orchestration du flow complet                              │
│  - Validation (asset, product status, cap)                  │
│  - Séquençage (conversion → supply)                         │
│  - Preview (read-only) et Invest (atomique)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────────┐    ┌──────────────────────┐          │
│   │  ExchangeService │    │  OfferService         │          │
│   │  - buy()         │    │  - subscribe()        │          │
│   │  - swap()        │    │  (ticket + cap + pool) │          │
│   │  - preview_buy() │    └──────────────────────┘          │
│   │  - preview_swap()│    ┌──────────────────────┐          │
│   └──────────────────┘    │  PoolLendingService   │          │
│                           │  - supply_commitment  │          │
│                           └──────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Responsabilités strictes** :
- `LendingInvestOrchestrator` : validation + séquençage (ne touche JAMAIS les balances)
- `ExchangeService` : conversion fiat→crypto ou crypto→crypto
- `OfferService.subscribe()` : validation tickets/cap + supply via PoolLendingService
- `PoolLendingService` : réservation de balance + commitment

---

## 3. Endpoints

### Preview (read-only, zero side-effect)

```
POST /api/lending/products/{product_id}/invest/preview

Body:
{
  "client_id": "uuid",
  "funding_asset": "EUR",
  "funding_amount": 1000
}

Response:
{
  "product_id": "uuid",
  "pool_asset": "USDC",
  "funding_asset": "EUR",
  "funding_amount": 1000.0,
  "conversion_type": "buy",
  "requires_conversion": true,
  "estimated_pool_asset_amount": 921.30,
  "estimated_supply_amount": 921.30,
  "conversion_fee": 4.63,
  "conversion_fee_asset": "USDC",
  "entry_asset_used": "USDC"
}
```

### Invest (exécution atomique)

```
POST /api/lending/products/{product_id}/invest

Body: (identique au preview)

Response:
{
  "status": "completed",
  "product_id": "uuid",
  "commitment_id": "uuid",
  "pool_id": "uuid",
  "funding_asset": "EUR",
  "funding_amount": 1000.0,
  "conversion_type": "buy",
  "entry_asset_used": "USDC",
  "total_pool_asset_received": 920.0,
  "amount_supplied": 920.0,
  "conversion_details": {
    "order_id": "uuid",
    "price": 1.087,
    "fee_amount": 4.6
  }
}
```

---

## 4. Flow d'investissement

### Cas 1 — Direct (funding_asset == pool_asset)

```
Client [USDC 2000] → InvestOrchestrator → subscribe() → supply_commitment
```

### Cas 2 — Fiat → Buy (EUR → USDC)

```
Client [EUR 1000] → InvestOrchestrator
  → ExchangeService.buy(EUR → USDC) → 920 USDC reçus
  → subscribe() → supply_commitment de 920 USDC
```

### Cas 3 — Crypto → Swap (BTC → USDC)

```
Client [BTC 0.1] → InvestOrchestrator
  → ExchangeService.swap(BTC → USDC) → 8400 USDC reçus
  → subscribe() → supply_commitment de 8400 USDC
```

---

## 5. Mapping Bundle → Exclusive Offer

| Concept | Bundle | Exclusive Offer |
|---------|--------|-----------------|
| Entry asset config | `pe_product_definitions.metadata_` | `lending_pool_products.entry_*` |
| Destination | Portfolio (multi-asset) | Pool (single asset) |
| Preview | `POST /bundle/invest/preview` | `POST /products/{id}/invest/preview` |
| Invest | `POST /bundle/invest` | `POST /products/{id}/invest` |
| Conversion | N SWAPs (1 par target) | 0 ou 1 (single target) |
| Cash leg | Oui (reliquat) | Non |
| Positions créées | PositionAtoms (spot+cash) | PoolSupplyCommitment |
| Orchestrateur | `BundleOrchestrator` | `LendingInvestOrchestrator` |

---

## 6. Fichiers modifiés / créés

| Fichier | Action |
|---------|--------|
| `api/services/lending/offer_models.py` | ✏️ Ajout `entry_asset_default`, `entry_assets_allowed` |
| `api/services/lending/offer_service.py` | ✏️ Ajout params dans `create_product`, exposition dans `_product_to_dict` |
| `api/services/lending/offer_router.py` | ✏️ Schémas invest, endpoints preview/invest |
| `api/services/lending/invest_orchestrator.py` | ✨ Nouveau — orchestrateur complet |
| `api/alembic/versions/077_add_entry_asset_to_lending_products.py` | ✨ Migration |
| `api/tests/test_lending_invest.py` | ✨ 20 tests |

---

## 7. Tests

**20 tests** couvrant :

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Entry asset model (defaults, resolution, persistence) | 4 | ✅ |
| Preview — direct (no conversion) | 2 | ✅ |
| Preview — fiat buy (EUR → USDC) | 1 | ✅ |
| Preview — crypto swap (BTC → USDC) | 1 | ✅ |
| Invest — direct supply (USDC → USDC) | 3 | ✅ |
| Invest — fiat buy (mocked) | 1 | ✅ |
| Invest — crypto swap (mocked) | 1 | ✅ |
| Validation — funding asset not allowed | 1 | ✅ |
| Validation — fiat always accepted | 1 | ✅ |
| Validation — product not investable (draft/closed) | 2 | ✅ |
| Validation — cap (capped + full rejection) | 2 | ✅ |
| current_raised — multi-investor accumulation | 1 | ✅ |

**Non-régression** : 49/49 tests passés (20 nouveaux + 29 existants)

---

## 8. Invariants respectés

| Invariant | Vérifié |
|-----------|---------|
| crypto_positions inchangé | ✅ |
| ExchangeService inchangé | ✅ |
| PoolLendingService inchangé | ✅ |
| Preview = zero side-effect | ✅ (test dédié) |
| Invest = atomique | ✅ |
| Bundle flow inchangé | ✅ |
| Borrow/Interest/Repay inchangés | ✅ |

---

## 9. Contrat Flutter (prêt pour intégration mobile)

### Catalogue enrichi (product detail)

Nouveaux champs exposés :
```json
{
  "entry_asset_default": "USDC",
  "entry_assets_allowed": ["USDC", "EUR", "BTC"]
}
```

### Flow mobile recommandé

| Écran | Données |
|-------|---------|
| Source selection | Filtre wallets par `entry_assets_allowed` |
| Amount entry | Appel preview → affiche estimation |
| Confirmation | Récapitulatif montant → conversion → supply |
| Processing | Appel invest → résultat |
