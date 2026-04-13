# Phase 2A.13 — Flutter Placements / Exclusive Offers (Post-Invest Surface)

## Objectif

Créer une surface Flutter dédiée aux **Placements** (yield products / lending), séparée intellectuellement de la surface Crypto, avec une UX identique à la page "Mes cryptos".

## Architecture

```
Dashboard (home_screen.dart)
  └── Row "Placements" → tap → PlacementsScreen
        └── PlacementPosition card → tap → PlacementDetailScreen
```

### Séparation produit

| Type                     | Section       |
|--------------------------|---------------|
| BTC / ETH / SOL          | **Crypto**    |
| Bundles crypto            | **Crypto**    |
| Lending / Exclusive Offers | **Placements** |

---

## Fichiers créés

### Flutter

| Fichier | Rôle |
|---------|------|
| `features/placements/data/placements_api.dart` | API service — fetch earn positions + lending dashboard |
| `features/placements/domain/models/placement_position.dart` | Modèles : `PlacementsData`, `EarnPositionItem`, `PlacementPosition` |
| `features/placements/presentation/screens/placements_screen.dart` | Écran liste — header + total balance + cards positions |
| `features/placements/presentation/screens/placement_detail_screen.dart` | Écran détail — hero image + position summary + metrics + pool info + status |

### Backend (FastAPI)

| Endpoint | Fichier |
|----------|---------|
| `GET /api/app/lending/earn/positions` | `api/services/test_clients/router.py` (wraps `get_earn_positions` with bootstrap client) |
| `GET /api/app/lending/dashboard` | `api/services/test_clients/router.py` (wraps `get_earn_borrow_dashboard`) |

### BFF Proxy (Next.js)

| Route | Cible backend |
|-------|---------------|
| `GET /api/mobile/flutter/lending/earn/positions` | → `GET /api/app/lending/earn/positions` |
| `GET /api/mobile/flutter/lending/dashboard` | → `GET /api/app/lending/dashboard` |

### Config Flutter

| Ajout | Fichier |
|-------|---------|
| `Config.lendingEarnPositionsUrl` | `core/config.dart` |
| `Config.lendingDashboardUrl` | `core/config.dart` |

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `features/home/presentation/screens/home_screen.dart` | Navigation "Placements" → `PlacementsScreen`, chargement données placements, enrichissement row dashboard |
| `core/config.dart` | Ajout URLs lending |
| `api/services/test_clients/router.py` | 2 nouveaux endpoints lending wrappés avec bootstrap client |

---

## Écran 1 — PlacementsScreen (liste)

### Structure UX (copie exacte de AllCryptoPositionsScreen)

1. **Hero section** (fond vert foncé `#0A2E1A`)
   - Titre : "Placements"
   - Sous-titre : balance totale EUR
   - Label : "N placement(s)"
2. **Liste de positions** dans une carte blanche avec coins arrondis (24px)
   - Chaque position = `TransactionTile` (même widget que les crypto)
   - Avatar : icône par catégorie (immobilier, énergie, tech) ou image projet
   - Titre : nom du projet
   - Sous-titre : APR + statut
   - Droite : valeur EUR + intérêts accumulés (vert)
3. **Empty state** si aucune position
   - Icône savings
   - Message + CTA "Explorer les offres" → OffersScreen
4. **Shimmer loading** (identique crypto)

### Data flow

```
PlacementsScreen
  ├── PlacementsApi.fetchEarnPositions() → financial data per asset
  ├── OffersRepository.getProjects() → CMS project metadata
  └── Client-side join by lendingAsset → PlacementPosition[]
```

---

## Écran 2 — PlacementDetailScreen (détail)

### Sections

1. **Hero** — image projet en plein écran + titre + catégorie
2. **Position summary** — montant investi, intérêts accumulés, valeur totale
3. **Métriques** — APR (vert), durée (bleu), statut (couleur dynamique)
4. **Pool info** — montant levé / cible + progress bar + nombre investisseurs + asset
5. **Status section** — message contextuel selon le statut :
   - `fundraising` → "En attente d'activation" (bleu)
   - `active` → "Génère des intérêts quotidiennement" (vert)
   - `repaid` → "Offre terminée" (gris)

---

## Dashboard — Integration

### Row "Placements" enrichie

Avant :
```
Placements
0 coffre          0,00 €
```

Après (avec données réelles) :
```
Placements
2 placements      12 450,00 €
```

### Navigation

- Tap sur row "Placements" → `PlacementsScreen`
- Retour du screen → refresh des données placements sur le dashboard

### Balance totale dashboard

La `numericBalance` de la row Placements est maintenant `totalValueEur` des earn positions, incluse dans le calcul de la balance totale du header.

---

## Mapping Backend → Flutter

| Backend (earn/positions) | Flutter (PlacementPosition) |
|--------------------------|----------------------------|
| `total_earn_value_eur` | `PlacementsData.totalValueEur` |
| `positions[].asset` | `EarnPositionItem.asset` |
| `positions[].total_supplied` | `totalSupplied` |
| `positions[].accrued_interest` | `accruedInterest` |
| `positions[].total_value` | `totalValue` |
| `positions[].value_eur` | `valueEur` |
| `positions[].apy` | `apy` (fallback if project.apy null) |

| Backend (projects) | Flutter (PlacementPosition) |
|---------------------|----------------------------|
| `project.title` | `projectTitle` |
| `project.imageUrl` | `projectImageUrl` |
| `project.category` | `projectCategory` |
| `project.lendingAsset` | Join key with earn position |
| `project.lendingStatus` | `status` |
| `project.durationMonths` | `durationMonths` |
| `project.raised` | `raised` |
| `project.target` | `target` |
| `project.investorsCount` | `investorsCount` |

---

## Status mapping

| Backend | Flutter label | Couleur |
|---------|--------------|---------|
| `fundraising` | "En levée" | `#3B82F6` (bleu) |
| `active` | "Actif" | `#059669` (vert) |
| `repaid` | "Terminé" | `#6B7280` (gris) |

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Zéro changement sur crypto screens | ✅ |
| Zéro changement sur wallets | ✅ |
| Zéro changement sur navigation existante | ✅ |
| Zéro changement sur ExchangeService | ✅ |
| Zéro changement sur crypto_positions | ✅ |
| Flutter analyze : 0 errors | ✅ |
| Python import : OK | ✅ |

---

## Compilation

```
$ flutter analyze lib/features/placements/
Analyzing placements...
No issues found!
```

```
$ python3 -c "from services.test_clients.router import bootstrap_router"
OK: bootstrap_router with lending endpoints
```
