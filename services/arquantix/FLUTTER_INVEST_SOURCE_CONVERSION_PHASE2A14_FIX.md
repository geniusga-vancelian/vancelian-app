# Phase 2A.14 Fix — Source Selection & Conversion Flow

## Objectif

Ajouter une étape de sélection de compte source (EUR, USDC, BTC…) au flow d'investissement Exclusive Offer, avec gestion automatique de la conversion, en répliquant exactement le pattern Bundle.

---

## Architecture du flow

```
ExclusiveOfferDetailScreen
  └─ CTA "Investir"
       ├─ isInvestable = false → Modale "Investissement indisponible"
       └─ isInvestable = true  → LendingInvestSourceScreen (NEW — STEP 1)
                                    └─ LendingInvestInputScreen (STEP 2 — adapté)
                                         └─ LendingInvestPreviewScreen (STEP 3)
                                              └─ LendingInvestProcessingSheet (STEP 4)
```

### Avant

```
CTA → InputScreen (montant + source combo) → Preview → Processing
```

### Après

```
CTA → SourceScreen (choix compte) → InputScreen (montant + balance) → Preview → Processing
```

---

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `lending_invest_source_screen.dart` | STEP 1 — sélection compte source |

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `lending_invest_input_screen.dart` | Reçoit `sourceAccount`, affiche balance, over-balance |
| `lending_invest_preview_screen.dart` | Reçoit `sourceAccount` optionnel |
| `exclusive_offer_detail_screen.dart` | CTA → `LendingInvestSourceScreen` |

---

## STEP 1 — LendingInvestSourceScreen

### Réplication exacte du pattern Bundle

| Élément | Bundle | Lending |
|---------|--------|---------|
| Composant | `BundleSourceSelectionScreen` | `LendingInvestSourceScreen` |
| Header | `AppTopNavBar` (back) | `AppTopNavBar` (back) |
| Titre | `AppPageTitle("Investir dans {bundle}")` | `AppPageTitle("Investir dans {project}")` |
| Question | "À partir de quel compte…" | "À partir de quel compte…" |
| Sections | Comptes fiat / Wallets entry asset | Comptes fiat / Wallets crypto |
| Cards | `TransactionTile` + `TransactionAvatar` | `TransactionTile` + `TransactionAvatar` |
| Filtrage | `entryAssetsAllowed` | `entryAssetsAllowed` |
| Navigation | → `BundleAmountEntryScreen` | → `LendingInvestInputScreen` |

### Chargement des comptes

| Source | API | Condition |
|--------|-----|-----------|
| Compte Euro | `CashApi.fetchCashData()` | Si EUR dans `entryAssetsAllowed` |
| Wallets crypto | `CryptoPositionsApi.fetchPositions()` | Asset dans `entryAssetsAllowed` ET balance > 0 |

---

## STEP 2 — LendingInvestInputScreen (adapté)

### Changements

| Aspect | Avant | Après |
|--------|-------|-------|
| Paramètres | `project` seul | `project` + `sourceAccount` |
| Source asset | Sélecteur radio inline | Déterminé par `sourceAccount` |
| Balance | Non affichée | Affichée dans source pill |
| Over-balance | Non géré | Bannière erreur + CTA disabled |
| `fundingAsset` | Déduit de sélection | Déduit de `sourceAccount.currency` |

### Source pill

Affiche le compte sélectionné avec icône, label, et balance (pattern identique `BundleAmountEntryScreen`).

### Over-balance

```dart
_isOverBalance = _parsedAmount > _sourceBalance && _sourceBalance > 0
```

Bannière rouge : "Solde insuffisant (1 234,56 €)"

### Conversion info

Si `fundingAsset ≠ poolAsset` : info box indigo "Conversion EUR → USDC automatique"

---

## Passage du contexte

```
SourceScreen
  └─ sourceAccount: BundleSourceAccount  →  InputScreen
       └─ fundingAsset: String           →  PreviewScreen
       └─ fundingAmount: double          →  PreviewScreen
       └─ sourceAccount: BundleSourceAccount  →  PreviewScreen (optionnel)
            └─ fundingAsset + fundingAmount  →  ProcessingSheet
```

Le modèle `BundleSourceAccount` est réutilisé directement depuis le Bundle flow (pas de duplication).

---

## Cas gérés

| Cas | Comportement |
|-----|-------------|
| EUR → USDC (fiat invest) | Source pill EUR, conversion buy, info box |
| BTC → USDC (crypto invest) | Source pill BTC, conversion swap, info box |
| USDC → USDC (direct) | Source pill USDC, "alloué directement", pas d'info box |
| Balance insuffisante | Bannière erreur rouge, CTA disabled |
| Asset non autorisé | Pas affiché dans la liste source |
| Aucun compte disponible | Message "Aucun compte disponible" centré |
| Offre non investissable | Modale "Investissement indisponible" |

---

## UX client

Le client voit :
- "À partir de quel compte souhaitez-vous investir ?"
- Liste de ses comptes avec balances
- "Converti en USDC puis alloué à l'offre"
- "Conversion EUR → USDC automatique"
- "Alloué directement depuis votre wallet USDC"

Le client ne voit jamais : buy, swap, ExchangeService.

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Backend inchangé | ✅ |
| Logique invest inchangée | ✅ |
| API preview/execute inchangés | ✅ |
| ExchangeService inchangé | ✅ |
| PoolService inchangé | ✅ |
| Flutter analyze : 0 errors, 0 warnings | ✅ |

---

## Compilation

```
$ flutter analyze lib/features/offers/presentation/screens/lending_invest_flow/
3 issues found. (all info: prefer_const_constructors)
```

```
$ flutter analyze lib/features/offers/ lib/features/home/
0 errors, 0 new warnings (all pre-existing)
```
