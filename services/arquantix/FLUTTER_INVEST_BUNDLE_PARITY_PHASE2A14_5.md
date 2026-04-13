# Phase 2A.14.5 — Flutter Invest Bundle Parity

## Objectif

Amener le flow Exclusive Offer au niveau exact du flow Bundle : sélection de source + conversion explicite + UI identique.

---

## Flow complet

```
CTA "Investir"
  └─ LendingInvestSourceScreen         (STEP 1 — NEW)
       └─ LendingInvestInputScreen     (STEP 2 — adapté)
            └─ LendingInvestPreviewScreen  (STEP 3)
                 └─ LendingInvestProcessingSheet (STEP 4)
```

---

## Mapping Bundle → Lending

| Bundle | Lending | Identique |
|--------|---------|-----------|
| `BundleSourceSelectionScreen` | `LendingInvestSourceScreen` | ✅ |
| `BundleAmountEntryScreen` | `LendingInvestInputScreen` | ✅ |
| `BundleConfirmationScreen` | `LendingInvestPreviewScreen` | ✅ |
| `BundleProcessingSheet` | `LendingInvestProcessingSheet` | ✅ |
| `BundleSourceAccount` | Réutilisé tel quel | ✅ |
| `BundleFlowHeaderDisk` | Réutilisé tel quel | ✅ |
| `TableInformationModule` | Réutilisé tel quel | ✅ |

---

## Composants DS utilisés (identiques au Bundle)

| Composant | Usage |
|-----------|-------|
| `AppTopNavBar` | Header source screen |
| `AppPageTitle` | Titre principal |
| `AppSectionTitle2` | Sections fiat / crypto |
| `TransactionTile` + `TransactionAvatar` | Liste de comptes |
| `BundleFlowHeaderDisk` | Header disks (back, icon) |
| `TableInformationModule` | Preview summary |
| `AppTypography.heroAmount` | Montant centré 48px |
| `AppTypography.sectionTitle` | Titre processing |
| `AppTypography.meta` | Sous-titres |
| `AppColors.indigo` | CTA, accents |
| `AppColors.errorBackground` / `errorText` | Over-balance |
| `AppSpacing.*` | Tous les espacements |
| `AppRadius.button` | FilledButton |
| `FilledButton` | Boutons processing sheet |

---

## Écran par écran

### STEP 1 — Source Selection

- Question : "À partir de quel compte souhaitez-vous investir ?"
- Comptes fiat : `CashApi.fetchCashData()` → "Compte Euro" + balance
- Wallets crypto : `CryptoPositionsApi.fetchPositions()` → filtré par `entryAssetsAllowed`
- Card : `AppColors.cardBackground`, borderRadius 24, shadow
- Items : `TransactionTile` avec `TransactionAvatar` (logo résolu via Config)
- Tap → `LendingInvestInputScreen(project, sourceAccount)`

### STEP 2 — Amount Entry

- Source pill : compte sélectionné (icône + label + balance formatée)
- Hidden input + heroAmount 48px centré
- Note contextuelle :
  - "Converti en USDC puis alloué à l'offre" (si conversion)
  - "Alloué directement depuis votre wallet USDC" (si direct)
- Over-balance : bannière rouge + CTA disabled
- Conversion info : info box indigo "Conversion EUR → USDC automatique"
- Bottom bar : CTA indigo h52 avec elevation 4

### STEP 3 — Preview / Confirmation

- Titre : "Vous êtes sur le point d'investir"
- Montant : heroAmount 36px
- Sous-titre : "dans {projet}"
- `TableInformationModule` :
  - Offre → nom du projet
  - Compte source → montant + asset
  - Conversion → type (si applicable)
  - Montant alloué → estimé en pool asset
  - Frais → si conversion
  - APR → pourcentage
- Info box indigo
- Bottom bar : back circle 48px + CTA "Confirmer l'investissement"

### STEP 4 — Processing / Success / Error

- Processing : cercle 64x64 textPrimary + spinner blanc + "Allocation dans l'offre…"
- Success : cercle + check + "Investissement réussi" + montant + CTAs
- Error : cercle + close + message + "Fermer"

---

## Cas edge couverts

| Cas | Gestion |
|-----|---------|
| Balance insuffisante | Bannière rouge, CTA disabled |
| Asset non autorisé | Non affiché dans la liste source |
| Aucun compte disponible | Message centré "Aucun compte disponible" |
| Offre non investissable | Modale avant le flow |
| Preview error | Message + bouton retry |
| Invest error | Message dans bottom sheet |
| Conversion impossible | Erreur backend propagée |

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Backend inchangé | ✅ |
| LendingInvestOrchestrator inchangé | ✅ |
| API preview/invest inchangés | ✅ |
| ExchangeService inchangé | ✅ |
| PoolService inchangé | ✅ |
| Crypto screens inchangés | ✅ |
| Bundle flow inchangé | ✅ |
| Flutter analyze : 0 errors, 0 warnings | ✅ |

---

## Compilation

```
$ flutter analyze lib/features/offers/presentation/screens/lending_invest_flow/
3 issues found. (all info: prefer_const_constructors — identical to bundle flow)
```
