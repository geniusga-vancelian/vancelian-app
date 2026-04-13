# Phase 2A.14 Fix — Lending Invest Flow DS Alignment

## Objectif

Refactorisation complète des 3 écrans du flow d'investissement Exclusive Offer pour utiliser strictement le Design System Vancelian et s'aligner pixel-perfect avec le flow Bundle.

---

## Composants remplacés

### Avant → Après

| Élément | Avant (custom) | Après (DS/Bundle) |
|---------|---------------|-------------------|
| **Header** | `AppBar` standard Flutter | `BundleFlowHeaderDisk` (disque 36x36 + back icon) |
| **Couleur CTA** | `Color(0xFF059669)` (vert custom) | `AppColors.indigo` |
| **Border radius cards** | 16 / 20 hardcodé | 24 (DS standard) |
| **Padding page** | 24 hardcodé | `AppSpacing.lg` (16) / `AppSpacing.xl` (20) |
| **Amount input** | `TextField` visible avec border | heroAmount centré 48px (hidden input pattern) |
| **Preview table** | Custom `_buildRow` + `Divider` | `TableInformationModule` (DS) |
| **Boutons** | `ElevatedButton` vert custom | `ElevatedButton` indigo + `FilledButton` (DS pattern) |
| **Processing circle** | `CircularProgressIndicator` vert 64x64 | Cercle 64x64 `textPrimary` + spinner blanc 28x28 |
| **Success icon** | `Icons.check_circle` vert 64px | Cercle 64x64 `textPrimary` + `check_rounded` blanc |
| **Error icon** | `Icons.error_outline` rouge 64px | Cercle 64x64 `textPrimary` + `close_rounded` blanc |
| **Bottom bar** | Aucune séparation | Bordure top `textPrimary.alpha(0.06)` |
| **Bottom bar CTA** | Simple `ElevatedButton` pleine largeur | Back button rond + `ElevatedButton` (preview) |
| **Sheet border radius** | 24 | 20 (bundle pattern) |
| **Sheet padding** | `fromLTRB(24, 16, 24, 24)` | `fromLTRB(xl, sm, xl, xxl)` = `fromLTRB(20, 8, 20, 24)` |
| **Typographie titre** | `titleMedium` / `titleLarge` | `sectionTitle` (processing), `titleLarge` (preview) |
| **Typographie sous-titre** | `bodyMedium` custom | `AppTypography.meta` |
| **Info box** | Vert/jaune custom | Indigo alpha 0.06 + borderRadius 14 (bundle pattern) |

---

## Mapping DS complet

### Tokens utilisés

| Token | Valeur | Usage |
|-------|--------|-------|
| `AppSpacing.xs` | 4 | Espacement minimal |
| `AppSpacing.sm` | 8 | Padding sheet top, inter-éléments |
| `AppSpacing.lg` | 16 | Padding page horizontal, espacement sections |
| `AppSpacing.xl` | 20 | Padding sheet horizontal |
| `AppSpacing.xxl` | 24 | Padding sheet bottom |
| `AppRadius.button` | 20 | FilledButton border radius |
| `AppColors.pageBackground` | #F5F5F5 | Fond de page |
| `AppColors.cardBackground` | white | Cards, pills, bottom bar buttons |
| `AppColors.textPrimary` | #000 | Textes, cercles processing |
| `AppColors.textSecondary` | #64748B | Sous-titres, meta, hints |
| `AppColors.indigo` | #6B5DFF | CTA, accents, info boxes |
| `AppColors.placeholderBg` | — | Bouton secondaire background |
| `AppColors.placeholderIcon` | — | Handle bar sheet |

### Composants DS utilisés

| Composant | Fichier | Usage |
|-----------|---------|-------|
| `BundleFlowHeaderDisk` | `bundle_invest_flow_controller.dart` | Header back button |
| `TableInformationModule` | `design_system/components/table_information_module.dart` | Preview summary rows |
| `TableInformationRowData` | idem | Data model pour chaque row |
| `AppTypography.heroAmount` | `design_system/atoms/app_typography.dart` | Montant centré (48px input, 28px success) |
| `AppTypography.sectionTitle` | idem | Titre processing sheet |
| `AppTypography.titleLarge` | idem | Titre preview |
| `AppTypography.titleMedium` | idem | Header title |
| `AppTypography.bodyMedium` | idem | CTA text, rows |
| `AppTypography.bodySmall` | idem | Notes, hints |
| `AppTypography.meta` | idem | Sous-titres processing |

---

## Structure écran par écran

### Input Screen (LendingInvestInputScreen)

```
Scaffold(backgroundColor: AppColors.pageBackground)
└── SafeArea → Column
    ├── Header (BundleFlowHeaderDisk back + title + disk icon)
    ├── Source pill (project info + selected asset)
    ├── Expanded → GestureDetector(onTap: openKeyboard)
    │   └── Column
    │       ├── Question text (titleLarge, w700, height 1.35)
    │       ├── heroAmount display (48px + hidden TextField)
    │       ├── Entry asset note (bodySmall, textSecondary)
    │       ├── [if multi-asset] Asset selector (card 24, check icons)
    │       └── Conversion hint (info box indigo/amber)
    └── Bottom bar (border top + ElevatedButton indigo, height 52)
```

### Preview Screen (LendingInvestPreviewScreen)

```
Scaffold(backgroundColor: AppColors.pageBackground)
└── SafeArea → Column
    ├── Header (BundleFlowHeaderDisk back + "Confirmation")
    ├── Expanded → SingleChildScrollView
    │   └── Column
    │       ├── "Vous êtes sur le point d'investir" (titleLarge, w700)
    │       ├── Amount (heroAmount 36px)
    │       ├── "dans {project}" (bodyMedium, textSecondary)
    │       ├── TableInformationModule(rows: [...])
    │       └── Info box (indigo alpha 0.06, borderRadius 14)
    └── Bottom bar (back circle 48x48 + CTA indigo)
```

### Processing Sheet (LendingInvestProcessingSheet)

```
Container(borderRadius: top 20, color: cardBackground)
└── SafeArea(top: false)
    └── Padding(fromLTRB: xl, sm, xl, xxl)
        └── Column
            ├── Handle bar (40x4, placeholderIcon alpha 0.5)
            └── Phase content:
                ├── processing: circle 64 textPrimary + spinner blanc + sectionTitle + meta
                ├── success: circle 64 textPrimary + check blanc + heroAmount 28 + 2 FilledButtons
                └── error: circle 64 textPrimary + close blanc + sectionTitle + FilledButton
```

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Logique API inchangée | ✅ |
| Navigation inchangée | ✅ |
| Logique invest inchangée | ✅ |
| CTA wiring inchangé | ✅ |
| Aucun nouveau composant DS créé | ✅ |
| Flutter analyze : 0 errors, 0 warnings | ✅ |

---

## Compilation

```
$ flutter analyze lib/features/offers/presentation/screens/lending_invest_flow/
5 issues found. (all info: prefer_const_constructors — same as bundle flow)
```
