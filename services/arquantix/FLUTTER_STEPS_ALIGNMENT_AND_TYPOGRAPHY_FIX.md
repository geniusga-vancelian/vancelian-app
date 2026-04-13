# Flutter — Steps Alignment & Typography Fix

## Changements appliqués

### 1. Alignement cercle ↔ titre

**Avant** : layout `IntrinsicHeight` + `Row(crossAxisAlignment: stretch)` — les
cercles étaient alignés avec le bloc global, pas avec le titre de chaque étape.
Le "2" tombait en bas du bloc, décalé du titre "Allocation".

**Après** : chaque étape est un `Row(crossAxisAlignment: start)` indépendant.
Le cercle a un `Padding(top: 1)` pour s'aligner visuellement avec la baseline
du titre. Le connecteur vertical est un widget séparé entre les steps.

### 2. Ligne verticale — 1px

**Avant** : `Container(width: 2)` avec `borderRadius` — trop épaisse.

**Après** : `Container(width: 1, color: AppColors.border)` dans un `SizedBox`
de `_circleSize` largeur avec `Center` — parfaitement centré sous le cercle,
fin et discret. Hauteur fixe de 20px avec gap de 4px de chaque côté.

### 3. Hiérarchie typographique

**Avant** :
- Titre step : `bodyMedium` (14px) w600
- Cercle : `bodyMedium` (13px custom) w700

**Après** :
- Titre step : `bodyMedium` **fontSize 15** w600 — légèrement plus dominant
- Cercle : `bodySmall` w700 (proportionnel au cercle réduit à 26px)

### 4. Dimensions cercle

**Avant** : 28px, `fontSize: 13` custom.

**Après** : 26px, `bodySmall` w700 — plus proportionné, laisse plus de
place au contenu sans écraser le texte.

---

## Avant / Après (structure)

### Avant

```
IntrinsicHeight
└─ Row(stretch)
   ├─ Column [Circle1, Expanded(line 2px), Circle2]   ← timeline
   └─ Column [Step1, SizedBox(24), Step2]              ← content
```

Cercle 2 collé en bas du bloc, désaligné du titre "Allocation".

### Après

```
Column
├─ StepRow(1) → Row(start) [Circle1 + Content1]
├─ Connector  → SizedBox(26w) > Center > Container(1px)
└─ StepRow(2) → Row(start) [Circle2 + Content2]
```

Chaque cercle aligné avec son propre titre, connecteur indépendant.

---

## Rendu visuel attendu

```
① Conversion                    ← cercle aligné avec le titre
   0.10 BTC → ≈ 6790.58 USDC
   Montant estimé selon le prix de marché

   │  ← 1px, centré, 20px hauteur

② Allocation                    ← cercle aligné avec le titre
   ≈ 6790.58 USDC alloués au
   programme de prêt
   Votre allocation sera affectée
   au programme selon le statut du produit
```

---

## Règles DS respectées

| Token | Utilisation |
|-------|-------------|
| `AppColors.cardBackground` | Fond carte |
| `AppColors.border` | Ligne verticale + cercle completed |
| `AppColors.indigo` (8% alpha) | Fond cercle |
| `AppColors.indigo` | Texte numéro |
| `AppColors.textPrimary` | Titres + contenu |
| `AppColors.textSecondary` | Sous-textes |
| `AppRadius.card` | Border radius carte |
| `AppTypography.title2` | Titre module |
| `AppTypography.bodyMedium` (15px w600) | Titre étape |
| `AppTypography.bodyMedium` | Texte principal |
| `AppTypography.bodySmall` | Sous-texte + numéro cercle |

Aucune couleur hardcodée. Aucun style inline arbitraire.

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| JSON parsing `fromJson` | Inchangé |
| `TransactionStepItem` | Inchangé |
| `LegalFooterNote` | Inchangé |
| Contenu texte / wording | Inchangé |
| Symbole ≈ | Inchangé |
| Logique conditionnelle | Inchangée |
| Flutter analyze | **0 issues** |

---

## Compilation

```
$ flutter analyze transaction_steps_module.dart lending_invest_preview_screen.dart
No issues found!
```
