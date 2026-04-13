# Bundle UI Entrypoints Integration Report

## Executive Summary

Les 3 points d'entrée du flow "Invest in Bundle" ont été branchés dans l'app Flutter de manière cohérente avec le design system existant. Le `BundleInvestFlowController` est réutilisé exclusivement — aucun flow dupliqué. Les flows BUY / SELL / SWAP ne sont pas modifiés.

### Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `design_system/components/featured_offer_card.dart` | Ajout `onActionTap` pour séparer tap carte ≠ tap bouton CTA |
| `design_system/components/assets_bundles_module.dart` | Ajout `onInvestTap` à `AssetsBundleItem`, propagation vers `FeaturedOfferCard.onActionTap` |
| `features/markets/data/product_catalog_api.dart` | Ajout param `onInvestTap` à `toAssetsBundleItem()` |
| `features/markets/presentation/widgets/crypto_bundles_widget.dart` | Import flow controller, callback `_onInvestTap` + `_canInvest` pour PE catalog items |
| `features/markets/presentation/screens/product_preview_screen.dart` | Chargement `ProductDetailItem`, construction `BundleItem`, callback `_onInvestTap` via `LandingPagePreviewScreen.onInvestTap` |
| `features/markets/presentation/screens/markets_screen.dart` | Bouton CTA global "Investir dans un bundle" sous la section Crypto Bundles |
| `features/landing_preview/presentation/screens/landing_page_preview_screen.dart` | Ajout `onInvestTap` propagé jusqu'au hero "Investir" button |

---

## Bundle Surfaces Found in the App

| Surface | Fichier | Rôle | Bundle data disponible |
|---------|---------|------|------------------------|
| **Markets screen — Crypto Bundles** | `markets_screen.dart` | Section "Crypto Bundles" avec carousel | Oui (PE catalog) |
| **CryptoBundlesWidget** | `crypto_bundles_widget.dart` | Widget réutilisable listant les bundles | Oui (PE) / Non (CMS) |
| **ProductPreviewScreen** | `product_preview_screen.dart` | Page détail produit (landing page) | Oui (via `ProductDetailItem`) |
| **LandingPagePreviewScreen** | `landing_page_preview_screen.dart` | Template CMS avec hero "Investir" button | Via callback |
| **VaultsMarketingCardsFeed** | `vaults_marketing_cards_feed.dart` | Sections CMS avec bundles | Non (données CMS insuffisantes) |
| **Home screen** | `home_screen.dart` | Dashboard principal | Aucun bundle affiché |
| **Offers screen** | `offers_screen.dart` | Page investissement exclusive offers | Aucun bundle affiché |

---

## Entrypoint A — Bundle List (Cartes Crypto Bundles)

### Comportement avant
- Tap carte bundle → `ProductPreviewScreen` (page détail)
- Bouton "Investir" sur la carte → même action que tap carte (redondant)

### Comportement après
- **Tap carte** → `ProductPreviewScreen` (page détail) — **inchangé**
- **Bouton "Investir"** → `BundleInvestFlowController.start(bundle)` — **STEP 1 directement**

### Changements techniques
1. `FeaturedOfferCard` : ajout `onActionTap` optionnel. Si fourni, le `AppMiniButton` "Investir" utilise `onActionTap` au lieu de `onTap`. Le tap carte reste sur `onTap`.
2. `AssetsBundleItem` : ajout `onInvestTap` optionnel, propagé vers `FeaturedOfferCard.onActionTap`.
3. `CryptoBundlesWidget` : pour les bundles PE catalog, `onInvestTap` construit un `BundleItem` et lance `BundleInvestFlowController.start(bundle)`.
4. Condition `_canInvest(product)` : vérifie que `portfolioId` est non-null et non-vide. Si le bundle n'a pas de portfolio provisionné, le bouton "Investir" fonctionne comme le tap carte (fallback vers détail).

### Refresh post-succès
Après `pop(true)` → `_load()` recharge la liste des bundles.

---

## Entrypoint B — Bundle Detail (Page Détail Produit)

### Comportement avant
- Hero "Investir" button sur la page produit → `onTap: () {}` (vide, ne fait rien)

### Comportement après
- Hero "Investir" button → `BundleInvestFlowController.start(bundle)` — **STEP 1 directement**

### Changements techniques
1. `ProductPreviewScreen` : chargement parallèle de `LandingPagePayload` + `ProductDetailItem` via `Future.wait`.
2. Construction du `BundleItem` depuis `ProductDetailItem` (portfolioId, allocations, entryAssetDefault, etc.).
3. Callback `_onInvestTap` passé à `LandingPagePreviewScreen.onInvestTap`.
4. `LandingPagePreviewScreen` : nouveau param `onInvestTap`, propagé à `_RuntimeLandingTemplatePage.onInvestTap`.
5. `_RuntimeLandingTemplatePage._buildLayoutPageLevel2()` : hero "Investir" `ActionButtonItem` utilise `widget.onInvestTap ?? () {}`.
6. Condition `canInvest` : si `portfolioId` absent, `onInvestTap` n'est pas passé et le bouton reste un no-op.

### Refresh post-succès
Après `pop(true)` → `_load()` recharge config + détail produit (page se rafraîchit).

---

## Entrypoint C — Global Bundle CTA

### Comportement avant
- Aucun point d'entrée global pour investir dans un bundle sans contexte préalable.

### Comportement après
- Bouton `OutlinedButton.icon` "Investir dans un bundle" visible sous la section Crypto Bundles dans Markets.
- Tap → `BundleInvestFlowController.startWithoutTarget(context)` — **STEP 0** (sélection du bundle).

### Changements techniques
1. `MarketsScreen` : import du `BundleInvestFlowController`.
2. Ajout d'un `OutlinedButton.icon` stylé avec `AppColors.indigo`, border subtle, icon `auto_awesome_mosaic_rounded`.
3. Méthode `_onInvestInBundle()` → `startWithoutTarget(context)`.

### Refresh post-succès
Après `pop(true)` → `_widgetsRefreshNonce++` déclenche la recharge du `CryptoBundlesWidget`.

### Design
- Bouton outline indigo, full-width sous les cartes bundles
- Icône mosaic (cohérente avec les écrans bundle)
- Texte "Investir dans un bundle"
- Ne prend pas plus de place qu'un CTA compact
- Visuellement distinct des trades spot (BUY/SELL)

---

## Navigation and Refresh Behavior

### Flow résultat cascade
Chaque point d'entrée récupère le `bool?` retourné par le flow controller :
- `true` → investissement réussi (completed ou partial) → refresh
- `false` ou `null` → annulation ou erreur → pas de refresh

### Refresh par point d'entrée

| Entrée | Action post-succès | Mécanisme |
|--------|-------------------|-----------|
| A — Bundle card "Investir" | Recharge la liste bundles | `CryptoBundlesWidget._load()` |
| B — Bundle detail "Investir" | Recharge page détail + données produit | `ProductPreviewScreen._load()` |
| C — Global CTA | Recharge le widget bundles | `_widgetsRefreshNonce++` |

### Navigation stack
- Entrée A/B : flow push → STEP 1→2→3→4 → `pop(true)` cascade → retour carte/détail
- Entrée C : flow push → STEP 0→1→2→3→4 → `pop(true)` cascade → retour Markets

---

## Non-Regression Notes

### Flows non impactés
- **BUY flow** : aucun fichier BUY modifié. `BuyFlowController`, `BuyFlowProcessingSheet`, `ExchangeApi` intacts.
- **SELL flow** : aucun fichier SELL modifié.
- **SWAP flow** : aucun fichier SWAP modifié.
- **Portfolio / Wallet stats** : non touchés.
- **WAC / PnL / Invariants** : backend inchangé.

### Composants modifiés de manière rétro-compatible
- `FeaturedOfferCard.onActionTap` : optionnel, fallback sur `onTap`. Les usages existants (Exclusive Offers, CMS bundles) ne passent pas `onActionTap` → comportement identique.
- `AssetsBundleItem.onInvestTap` : optionnel. Les usages CMS (VaultsMarketingCardsFeed) ne le passent pas → aucun changement.
- `LandingPagePreviewScreen.onInvestTap` : optionnel. Les Vaults et autres landing pages ne le passent pas → hero button reste `() {}`.

### Bundle CMS (non-PE)
Les bundles chargés depuis le CMS (`WidgetAssetsBundleItem`) n'ont pas de `portfolioId` ni d'allocations structurées. Le bouton "Investir" sur ces cartes conserve le comportement existant (même action que tap carte → redirection CMS). Seuls les bundles PE catalog bénéficient du flow invest.

### Tests backend
8/8 tests Phase 2 `test_bundle_orchestrator.py` passent sans régression.

### Flutter analyze
0 erreur, 0 warning propre dans les fichiers modifiés. Tous les warnings détectés sont préexistants.

---

## Final Status

| Composant | Status |
|-----------|--------|
| Entrée A — Carte bundle "Investir" (PE catalog) | ✅ Branché |
| Entrée A — Carte bundle "Investir" (CMS) | ⚠️ Pas de portfolioId → fallback tap carte |
| Entrée B — Hero "Investir" page détail | ✅ Branché |
| Entrée C — Global CTA Markets | ✅ Branché |
| Séparation tap carte ≠ tap CTA | ✅ `onActionTap` / `onInvestTap` |
| Refresh post-succès (A) | ✅ `_load()` |
| Refresh post-succès (B) | ✅ `_load()` |
| Refresh post-succès (C) | ✅ `_widgetsRefreshNonce++` |
| BUY / SELL / SWAP non-régression | ✅ Aucune modification |
| Backend tests | ✅ 8/8 passent |
| Flutter analyze | ✅ 0 erreur propre |
| Design cohérence | ✅ CTA indigo, icon mosaic, wording "Investir" |
