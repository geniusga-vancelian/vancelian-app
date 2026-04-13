# Flutter — Exclusive Offer Confirmation 2-Step UX

## Résumé

Refactorisation de l'écran de confirmation d'investissement (`LendingInvestPreviewScreen`)
pour remplacer le tableau plat par un module 2 étapes clair et narratif.

---

## Avant / Après

### Avant (TableInformationModule)

```
┌──────────────────────────────────────┐
│  Offre          │ Offer-xyz          │
│  Compte source  │ 1 000,00 €         │
│  Conversion     │ Achat (fiat→crypto) │
│  Montant alloué │ 1 155.07 USDC      │
│  APR            │ 11.0%              │
└──────────────────────────────────────┘
```

Problèmes :
- Tableau plat sans hiérarchie
- Wording technique ("Achat fiat→crypto", "Swap crypto→crypto")
- Pas de distinction claire entre les 2 opérations

### Après (_ExclusiveOfferInvestStepsCard)

```
┌──────────────────────────────────────┐
│ Étapes de votre investissement       │
│                                      │
│ ① Conversion                         │
│   1 000,00 €  →  1 155.07 USDC      │
│   Montant converti selon le prix     │
│   de marché estimé                   │
│ ─────────────────────────────────── │
│ ② Allocation                         │
│   1 155.07 USDC investis dans        │
│   l'offre                            │
│   Votre placement commencera à       │
│   générer du rendement selon le      │
│   statut du produit                  │
│ ─────────────────────────────────── │
│ Rendement annuel (APR)    [11.0 %]   │
└──────────────────────────────────────┘
```

---

## Structure visuelle

- **Carte blanche** unique avec `AppRadius.card` (12px) et ombre légère
- **Titre** : "Étapes de votre investissement" (`AppTypography.title2`)
- **2 blocs d'étape** identiques en structure :
  - Badge numéroté (cercle indigo 8% opacity, chiffre w700)
  - Titre de l'étape (w600)
  - Contenu principal (montants en w600, flèche en textSecondary)
  - Sous-texte descriptif (bodySmall, textSecondary)
- **Séparateurs** : `Divider` 6% opacity entre chaque section
- **APR** : badge vert en bas du module (`#059669` 10% bg)

---

## Cas gérés

### Cas A — Direct (USDC → USDC)

Étape 1 affiche :
```
✓ Aucune conversion nécessaire
```
Pas de sous-texte. Icône check verte.

Étape 2 :
```
1 000.00 USDC investis dans l'offre
```

### Cas B — Fiat → Target (EUR → USDC)

Étape 1 :
```
1 000,00 €  →  1 155.07 USDC
Montant converti selon le prix de marché estimé
```

Étape 2 :
```
1 155.07 USDC investis dans l'offre
```

### Cas C — Crypto → Target (BTC → USDC)

Étape 1 :
```
0.100000 BTC  →  6 857.53 USDC
Montant converti selon le prix de marché estimé
```

Étape 2 :
```
6 857.53 USDC investis dans l'offre
```

---

## Microcopy

| Élément | Texte |
|---------|-------|
| Titre écran | "Confirmation" |
| Accroche | "Vous êtes sur le point d'investir" |
| Titre bloc | "Étapes de votre investissement" |
| Étape 1 | "Conversion" |
| Sous-texte 1 | "Montant converti selon le prix de marché estimé" |
| Étape 2 | "Allocation" |
| Sous-texte 2 | "Votre placement commencera à générer du rendement selon le statut du produit" |
| Cas direct | "Aucune conversion nécessaire" |
| APR label | "Rendement annuel (APR)" |

### Wording interdit (jamais affiché)

- buy / swap / trade
- ExchangeService / PoolService
- order / execution
- lending orchestration

---

## Design System — Composants utilisés

| Composant | Usage |
|-----------|-------|
| `AppColors.cardBackground` | Fond carte |
| `AppColors.textPrimary` | Titres, montants |
| `AppColors.textSecondary` | Sous-textes, labels |
| `AppColors.indigo` | Badge numéroté, montant converti |
| `AppTypography.title2` | Titre du bloc |
| `AppTypography.bodyMedium` | Montants, titres d'étape |
| `AppTypography.bodySmall` | Sous-textes descriptifs |
| `AppRadius.card` | Rayon carte (12px) |
| `AppRadius.sm` | Rayon badge APR (8px) |
| `AppSpacing.*` | Espacements standards |
| `BundleFlowHeaderDisk` | Bouton retour header |

Aucun nouveau composant DS global créé. Widget local `_ExclusiveOfferInvestStepsCard` uniquement.

---

## Fichier modifié

`mobile/lib/features/offers/presentation/screens/lending_invest_flow/lending_invest_preview_screen.dart`

---

## Non-régression

| Élément | Modifié ? |
|---------|-----------|
| API preview | ❌ |
| API invest | ❌ |
| Navigation | ❌ |
| CTA "Confirmer" | ❌ |
| Processing sheet | ❌ |
| Success sheet | ❌ |
| Header | ❌ |
| Hero amount | ❌ |
| Bottom bar | ❌ |

---

## Compilation

```
$ flutter analyze lending_invest_preview_screen.dart
No issues found!
```
