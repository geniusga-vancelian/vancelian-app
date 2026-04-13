# Architecture et layout — Page d’accueil (Home / Dashboard)

Document de référence pour étudier et optimiser le layout de la page d’accueil (HomeScreen) et du template dashboard.

---

## 1. Vue d’ensemble

La page repose sur un **Stack** à 4 couches (de l’arrière vers l’avant) :

1. **Arrière-plan zone header** — Image (grain-bleu / grain-gris) en `headerBackground` du template : même taille que le header, positionnée derrière le Header 1.
2. **Header 1** (visuel) — `WalletHeader` : fond transparent, navbar, Balance, line chart, boutons d’action.
3. **Scroll** — `CustomScrollView` (optionnellement enveloppé dans un indicateur de refresh) : réserve de hauteur pour le header, puis sheet (carte), puis contenu.
4. **Header 2** (interaction) — `WalletHeaderHitOverlay` : overlay transparent de même taille que le header, zones cliquables uniquement (avatar, icônes, période, Balance, boutons). Le line chart n’est pas cliquable.

Le header est fixe (pas de parallax).

---

## 2. Schéma du stack (ordre Z)

```
┌─────────────────────────────────────────────────────────────────┐
│  Scaffold(backgroundColor: 0xFFF2F2F2)                           │
│  └── Stack                                                      │
│        ├── [0] Positioned(headerBackground)  ← Image grain      │
│        │         top: 0, height: headerHeight     │
│        │                                                         │
│        ├── [1] Positioned(header)            ← Header 1 (visuel) │
│        │         top: 0, height: headerHeight     │
│        │                                                         │
│        ├── [2] CustomMaterialIndicator? > CustomScrollView      │
│        │         (slivers ci‑dessous)                           │
│        │                                                         │
│        └── [3] Positioned(headerInteractionOverlay)             │
│                  ← Header 2 (zones cliquables)                  │
│                  top: 0, height: headerHeight     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Constantes de layout (valeurs réelles)

### 3.1 DashboardLayoutConstants (`dashboard_scroll_template.dart`)

| Constante | Valeur | Rôle |
|-----------|--------|------|
| `moduleHorizontalMargin` | `AppSpacing.lg` = **16** | Marge horizontale des modules (sheet, contenu) |
| `sheetOverlapTopPadding` | **20** | Espace vertical entre la réserve du header et la carte (sheet) |
| `moduleGap` | `AppSpacing.xxl` = **24** | Espace vertical entre sections (ex. entre carte et Flash info) |
| `bottomNavBarHeight` | **56** | Hauteur réservée pour la barre de navigation |
| `bottomNavBarMargin` | **8** | Marge sous la nav bar |

### 3.2 HomeScreen — hauteur du header

| Constante | Valeur | Rôle |
|-----------|--------|------|
| `_headerHeightFraction` | **0.60** | 60 % de la hauteur moins 2 × marge générale (16) d’écran |

Calcul :  
`headerHeight = (screenHeight * 0.60 - 2 * _headerGeneralMargin).clamp(0, ∞)` avec `_headerGeneralMargin = 16`

### 3.3 WalletHeader / WalletHeaderHitOverlay

| Constante | Valeur (px) | Rôle |
|-----------|-------------|------|
| `walletHeaderNavBarHeight` | **56** | Hauteur de la barre (avatar + icônes) |
| `_navbarHorizontalMargin` | **16** | Marge horizontale navbar |
| `_balanceModuleEstimatedHeight` | **100** | Estimation hauteur bloc Balance (centrage / chart) |
| `_balanceModuleHeight` (overlay) | **100** | Hauteur zone clic Balance dans Header 2 |
| `_gapBalanceChart` | **12** | Espace entre bloc Balance et line chart |
| `_balancePositionFactor` | **0.25** | Position verticale du bloc Balance dans la zone étendue (premier quart) |
| `_periodRowOffsetFromTop` | **67** | Offset du haut du bloc Balance au haut de la ligne période |
| `_periodRowHeight` | **26** | Hauteur zone période (0% · All time) |
| `_periodHitWidth` | **180** | Largeur zone clic période dans l’overlay |
| `_actionButtonsStripHeight` | **120** | Hauteur bande des boutons (Déposer, Envoyer, Acheter, Plus) |
| `_avatarWidth` | **40** | Largeur zone avatar |
| `_iconSize` | **48** | Taille zone icônes navbar (graphique, notifications) |

---

## 4. Structure du CustomScrollView (slivers)

Ordre des slivers (de haut en bas) :

| # | Sliver | Contenu | Remarque |
|---|--------|--------|----------|
| 1 | `SliverToBoxAdapter(SizedBox(height: headerHeight))` | Vide | Réserve la place du header ; `IgnorePointer` pour que les taps passent au Header 2 |
| 2 | (optionnel) `contentBeforeSheet` | — | Non utilisé sur HomeScreen |
| 3 | `sheetChild` (si non null) | `WalletsModule` (carte « My account ») | `Padding(horizontal)` + `Padding(top: sheetOverlapTopPadding)` — pas de chevauchement avec le header |
| 4 | Contenu principal | `content` = `_buildContentBelowSheet()` | Directement sous le sheet |
| 5 | `SizedBox(height: reserved)` | Vide | Réserve le bas (nav + marge + safe inset) |

Le sheet et le contenu sont affichés sous la réserve du header, sans décalage ni superposition.

---

## 5. Layout du Header 1 (WalletHeader)

L’image de fond (grain-bleu / grain-gris) est gérée au niveau de la page dans `DashboardScrollTemplate` (`headerBackground`), pas dans le header. Le header a un fond transparent.

Structure interne (Column dans un Stack, fond transparent) :

```
Stack
└── Column
      ├── _buildNavbar()                    ← hauteur 56 (SafeArea top: false)
      ├── Expanded
      │     └── LayoutBuilder
      │           └── Column (si showLineChart)
      │                 ├── Spacer(flex: 1)
      │                 ├── _BalanceModule   ← titre + montant + période
      │                 ├── Spacer(flex: 1)
      │                 ├── SizedBox(12)     ← gapBalanceChart
      │                 └── LineChartModule  ← hauteur = 50% du reste disponible
      └── _buildButtons()                  ← ActionButtonModule (SafeArea top: false)
```

- **Zone étendue** (entre navbar et boutons) :  
  `availableHeight = constraints.maxHeight` dans le `LayoutBuilder`.  
- **Line chart** :  
  `chartHeight = (availableHeight - 12 - 100) * 0.50` (clamp ≥ 0).  
- Les **boutons** sont en dehors du `SafeArea` bottom pour coller en bas du header.

---

## 6. Layout du Header 2 (WalletHeaderHitOverlay)

Overlay transparent, même `headerHeight` que le Header 1. Zones cliquables uniquement (pas de rendu visuel) :

- **Navbar** : `top: topPadding`, `height: 56` — avatar (40), spacer, graphique (48), notifications (48).
- **Module Balance** (si `onBalanceTap != null`) :  
  `balanceTop` + hauteur 100, centré, zone 220×100.
- **Période** (si `onPeriodTap != null`) :  
  `periodTop` (balanceTop + 67), hauteur 26, largeur 180, centré.
- **Bande boutons** :  
  `bottom: bottomPadding`, `height: 120`, 4 zones `Expanded` (Déposer, Envoyer, Acheter, Plus).

Calcul des positions (overlay) :

- `expandedHeight = headerHeight - topPadding - 56 - 120 - bottomPadding`
- `balanceTop = topPadding + 56 + (expandedHeight - 112) * 0.25`
- `periodTop = balanceTop + 67`

Le **line chart** n’a pas de zone dédiée : les taps sur cette zone traversent l’overlay (base `IgnorePointer`) et vont au scroll.

---

## 7. Contenu sous la carte (HomeScreen)

`_buildContentBelowSheet()` retourne une `Column` avec :

- `Padding(top: moduleGap, bottom: 24)`
- `ExclusiveOffersCarousel`
- `SizedBox(height: moduleGap)`
- `BlogNews` (Flash info)
- `SizedBox(height: moduleGap)`

États particuliers : loading (CircularProgressIndicator), erreur (_buildError).

---

## 8. Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `lib/features/home/presentation/screens/home_screen.dart` | Page d’accueil : calcule headerHeight, construit header + overlay, sheet, content, refresh |
| `lib/features/wallet/widgets/dashboard_scroll_template.dart` | Template : Stack (header + scroll + overlay), slivers, constantes partagées |
| `lib/features/wallet/widgets/wallet_header.dart` | Header 1 (WalletHeader), Header 2 (WalletHeaderHitOverlay), _BalanceModule, navbar, boutons |
| `lib/design_system/atoms/app_spacing.dart` | `AppSpacing.lg` = 16, `AppSpacing.xxl` = 24 |

---

## 9. Pistes d’optimisation du layout

- **Header**  
  - Ajuster `_headerHeightFraction` (0.60) et `_headerGeneralMargin` (16) selon device (petit écran vs tablette).  
  - Rendre `_balancePositionFactor` et le partage Balance / chart (50 %) configurables ou responsives.

- **Marges et espacements**  
  - Unifier `moduleHorizontalMargin` (16) avec les autres écrans.  
  - Réviser `sheetOverlapTopPadding` (20) et `moduleGap` (24) pour un rythme vertical cohérent.

- **Overlay (Header 2)**  
  - Vérifier que `balanceTop` / `periodTop` restent alignés avec le Header 1 sur toutes les tailles d’écran et safe areas.  
  - Si besoin, dériver les constantes (ex. _periodRowOffsetFromTop) de la hauteur réelle du _BalanceModule.

- **Performance**  
  - Le scroll utilise `clipBehavior: Clip.none` ; garder un œil sur le repaint quand le sheet et le contenu dépassent.

- **Accessibilité**  
  - Toutes les zones cliquables du Header 2 ont déjà des `Semantics` (button + label). Vérifier l’ordre de focus et les contrastes (Header 1).

---

*Dernière mise à jour : généré pour étude et optimisation du layout de la page d’accueil.*
