# Phase 2A.14 — Flutter Exclusive Offer Invest Flow (E2E)

## Résumé

Flow d'investissement complet pour les Exclusive Offers : saisie → preview → processing → succès, avec navigation vers Placements après investissement.

---

## Architecture

```
ExclusiveOfferDetailScreen
  └─ CTA "Investir"
       ├─ isInvestable = false → Modale "Investissement indisponible"
       └─ isInvestable = true  → LendingInvestInputScreen
                                    └─ LendingInvestPreviewScreen
                                         └─ LendingInvestProcessingSheet (bottom sheet)
                                              ├─ succès → CTA "Voir dans Placements"
                                              └─ erreur → message + fermer
```

---

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `mobile/lib/features/offers/data/lending_invest_api.dart` | API client Flutter (preview + execute) |
| `mobile/lib/features/offers/presentation/screens/lending_invest_flow/lending_invest_input_screen.dart` | Écran 1 — saisie montant + source asset |
| `mobile/lib/features/offers/presentation/screens/lending_invest_flow/lending_invest_preview_screen.dart` | Écran 2 — affichage preview + confirmation |
| `mobile/lib/features/offers/presentation/screens/lending_invest_flow/lending_invest_processing_sheet.dart` | Écran 3+4 — processing + success/error (bottom sheet) |
| `web/src/app/api/mobile/flutter/lending/products/[productId]/invest/preview/route.ts` | BFF proxy → invest preview |
| `web/src/app/api/mobile/flutter/lending/products/[productId]/invest/route.ts` | BFF proxy → invest execute |

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `web/src/app/api/projects/route.ts` | Ajout `lendingProductId`, `entryAssetDefault`, `entryAssetsAllowed` |
| `mobile/lib/features/offers/domain/models/offer_project.dart` | Ajout des 3 champs invest |
| `mobile/lib/features/offers/data/offers_api.dart` | Parsing des 3 nouveaux champs |
| `mobile/lib/features/offers/presentation/screens/exclusive_offer_detail_screen.dart` | CTA → vrai flow invest |
| `mobile/lib/core/config.dart` | URLs invest preview/execute |
| `api/services/test_clients/router.py` | 2 endpoints bootstrap (preview + invest) |

---

## Écran 1 — Input (LendingInvestInputScreen)

- Carte projet (titre + APR + catégorie)
- Champ montant numérique avec autofocus
- Sélecteur source asset (radio buttons) si `entryAssetsAllowed.length > 1`
- Indication conversion :
  - Vert "alloué directement" si source = pool asset
  - Jaune "sera converti en USDC" si conversion requise
- CTA "Continuer" → preview

## Écran 2 — Preview (LendingInvestPreviewScreen)

- Appel API : `POST /api/lending/products/{id}/invest/preview`
- Affichage : projet, source, conversion type, montant alloué estimé, frais, APR
- Loading + error states avec retry
- CTA "Confirmer l'investissement" → processing sheet

## Écran 3 — Processing (LendingInvestProcessingSheet)

- Bottom sheet non-dismissible
- Spinner + étapes textuelles :
  - "Conversion EUR → USDC…" (si applicable)
  - "Allocation dans l'offre…"
- Appel API : `POST /api/lending/products/{id}/invest`

## Écran 4 — Success (intégré dans ProcessingSheet)

- Icône check vert
- Montant alloué
- Nom du projet
- CTA primaire : "Voir dans Placements" → PlacementsScreen
- CTA secondaire : "Fermer"

---

## API Layer

### LendingInvestApi

```dart
previewInvest({productId, fundingAsset, fundingAmount}) → LendingInvestPreviewResult
executeInvest({productId, fundingAsset, fundingAmount}) → LendingInvestResult
```

### LendingInvestPreviewResult

| Champ | Type |
|-------|------|
| productId | String |
| poolAsset | String |
| fundingAsset | String |
| fundingAmount | double |
| conversionType | String (none/buy/swap) |
| requiresConversion | bool |
| estimatedPoolAssetAmount | double |
| estimatedSupplyAmount | double |
| entryAssetUsed | String |
| conversionFee | double? |
| conversionFeeAsset | String? |

### LendingInvestResult

| Champ | Type |
|-------|------|
| status | String |
| commitmentId | String? |
| poolId | String? |
| fundingAsset | String |
| fundingAmount | double |
| conversionType | String |
| entryAssetUsed | String |
| totalPoolAssetReceived | double |
| amountSupplied | double |

---

## Pipeline de données enrichi

```
Backend (offer_service.py)
  └─ get_lending_data_for_projects()
       ├─ lending_product_id ← NEW
       ├─ entry_asset_default ← NEW
       └─ entry_assets_allowed ← NEW
            │
BFF (web/src/app/api/projects/route.ts)
  └─ lendingProductId, entryAssetDefault, entryAssetsAllowed ← NEW
            │
Flutter (OfferProject)
  └─ lendingProductId, entryAssetDefault, entryAssetsAllowed ← NEW
            │
InvestInputScreen
  └─ Uses entryAssetsAllowed for source selector
  └─ Uses lendingProductId for API calls
```

---

## Cas gérés

| Cas | Comportement |
|-----|-------------|
| Direct invest (source = pool asset) | Pas de conversion, allocation directe |
| Fiat invest (EUR → USDC) | Conversion buy, puis allocation |
| Crypto invest (BTC → USDC) | Conversion swap, puis allocation |
| Offre non investissable | Modale "Investissement indisponible" |
| Preview error | Message d'erreur + bouton retry |
| Invest error | Message d'erreur dans bottom sheet |
| Product ID manquant | Message d'erreur explicite |

---

## Navigation post-succès

```
Success Sheet
  ├─ "Voir dans Placements" → push PlacementsScreen (refresh automatique)
  └─ "Fermer" → pop(true) → cascade pop → retour ExclusiveOfferDetailScreen
```

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Zéro changement moteur lending | ✅ |
| Zéro changement ExchangeService | ✅ |
| Zéro changement PoolService | ✅ |
| Zéro changement crypto screens | ✅ |
| Zéro changement bundles | ✅ |
| Zéro changement placements | ✅ |
| Flutter analyze : 0 errors | ✅ |
| Python import : OK | ✅ |
| Backward compatible API | ✅ (3 champs additifs) |

---

## Compilation

```
$ flutter analyze lib/features/offers/presentation/screens/lending_invest_flow/
  lib/features/offers/data/lending_invest_api.dart
No issues found!
```

```
$ python3 -c "from services.test_clients.router import bootstrap_router"
OK: bootstrap_router with lending invest endpoints
```
