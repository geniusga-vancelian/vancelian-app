# Flutter — Confirmation Steps UI Refinement

## Changements appliqués

### 1. Séparateurs horizontaux supprimés

Toutes les `Divider()` entre les étapes et avant le bloc APR ont été retirées.

### 2. Timeline verticale ajoutée

Les deux badges numérotés sont désormais reliés par une ligne verticale continue
qui utilise `IntrinsicHeight` + `Expanded` pour s'adapter dynamiquement au contenu.

Structure :

```
Column(
  ① cercle indigo 28px
  │  ligne verticale 2px (AppColors.border)
  ② cercle indigo 28px
)
```

La ligne ne déborde pas au-delà des cercles grâce à un `margin` vertical de 6px.

### 3. Bloc APR supprimé

Le "Rendement annuel (APR) 11.0 %" a été retiré du module. Cette information
est déjà visible sur la page détail de l'offre et n'est pas transactionnelle.

### 4. Symbole ≈ ajouté sur les montants estimés

Tous les montants en asset cible (résultat de conversion) sont préfixés par `≈` :

- Step 1 : `0.10 BTC → ≈ 6780.93 USDC`
- Step 2 : `≈ 6780.93 USDC investis dans l'offre`

Le ≈ n'apparaît PAS :
- sur le montant source (EUR, BTC)
- en cas de direct invest (pas de conversion → montant exact)

### 5. Microcopy ajustée

| Élément | Avant | Après |
|---------|-------|-------|
| Sous-texte étape 1 | "Montant converti selon le prix de marché estimé" | "Montant estimé selon le prix de marché" |
| Sous-texte étape 2 | "Votre placement commencera à générer du rendement selon le statut du produit" | "Génère du rendement selon le statut du produit" |

---

## Avant / Après

### Avant

```
┌──────────────────────────────────────┐
│ Étapes de votre investissement       │
│                                      │
│ (1) Conversion                       │
│     0.100000 BTC → 6780.93 USDC     │
│     Montant converti selon le prix   │
│     de marché estimé                 │
│ ──────────────────────────────────── │
│ (2) Allocation                       │
│     6780.93 USDC investis dans       │
│     l'offre                          │
│ ──────────────────────────────────── │
│ Rendement annuel (APR)    [11.0 %]   │
└──────────────────────────────────────┘
```

### Après

```
┌──────────────────────────────────────┐
│ Étapes de votre investissement       │
│                                      │
│ ① Conversion                         │
│ │  0.10 BTC → ≈ 6780.93 USDC        │
│ │  Montant estimé selon le prix      │
│ │  de marché                         │
│ │                                    │
│ ② Allocation                         │
│    ≈ 6780.93 USDC investis dans      │
│    l'offre                           │
│    Génère du rendement selon le      │
│    statut du produit                 │
└──────────────────────────────────────┘
```

---

## Justification UX

| Décision | Raison |
|----------|--------|
| Suppression dividers | Rendu plus clean, évite l'effet "tableau bancaire" |
| Timeline verticale | Progression narrative claire, pattern UX standard pour les flows |
| Suppression APR | Info non transactionnelle, déjà visible dans la fiche offre |
| Symbole ≈ | Transparence : le montant est une estimation au prix de marché |
| Microcopy raccourcie | Plus premium, moins verbeux, même information |

---

## Cas de rendu

### Direct (USDC → USDC)

```
① Conversion
│  ✓ Aucune conversion nécessaire
│
② Allocation
   1000.00 USDC investis dans l'offre
   Génère du rendement selon le statut du produit
```

### Fiat (EUR → USDC)

```
① Conversion
│  1 000,00 € → ≈ 1155.07 USDC
│  Montant estimé selon le prix de marché
│
② Allocation
   ≈ 1155.07 USDC investis dans l'offre
   Génère du rendement selon le statut du produit
```

### Crypto (BTC → USDC)

```
① Conversion
│  0.100000 BTC → ≈ 6780.93 USDC
│  Montant estimé selon le prix de marché
│
② Allocation
   ≈ 6780.93 USDC investis dans l'offre
   Génère du rendement selon le statut du produit
```

---

## Compilation

```
$ flutter analyze lending_invest_preview_screen.dart
No issues found!
```
