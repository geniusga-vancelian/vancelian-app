# Design System — Webapp (portail `/app/*`)

> Handoff **Webapp-full.zip** (mai 2026) — mobile-first, pixel-aligned sur le prototype `design_handoff_vancelian/`.

Le **site marketing** conserve son DS dans `vancelian-tokens.css` ; il n’est **pas** modifié par ce pack.

## Activation

Le layout racine pose `data-v-ds="app"` sur `<body>` pour toutes les routes `/app/*` (voir `src/app/layout.tsx`).

Les variables `--v-*` et les classes composants (`.btn`, `.card-simple`, `.v-eyebrow`, …) ne s’appliquent qu’à ce scope.

## Fichiers

| Fichier | Rôle |
|---|---|
| `public/app-ds/colors_and_type.css` | Tokens + typo (`vancelian.css` handoff) |
| `public/app-ds/layout.css` | Shell, grille, `.mstick`, `.actu`, `.mchain`, … |
| `public/app-ds/borrow-layout-patterns.css` | Emprunts : `.loan`, `.brw-cta`, `.brw-explain`, … |
| `src/styles/app/vancelian-app-tokens.css` | Projection scoped `[data-v-ds="app"]` |
| `src/styles/app/vancelian-app-components.css` | Boutons, forms, `.avt--*` (+ `safran`) |
| `src/styles/app/borrow-layout-patterns.css` | Même patterns emprunts, scoped app |
| `src/components/design-system/app/*` | Wrappers React |
| `scripts/sync-webapp-full-design-system.mjs` | Sync zip → `public/app-ds` + manifest |

## Différences clés vs website

| Règle | Website | Webapp |
|---|---|---|
| Carte produit | `#F2F1ED` (`--v-card`) | `#FFFFFF` (`.card-simple` / `.v-card`) |
| Warning | Terracotta | Safran `#C99A2E` |
| Account dot cryptos | — | `avt--safran` (safran) |
| Eyebrow | 11px / 0.05em | 13px / 0.08em / 600 (`.v-eyebrow`) |
| Mobile ≤640px | — | `.mchain` (wallet + réseau) · `.mstick` (CTA sticky) |
| `col-side` ≤960px | masqué (ancien) | **suite du contenu** sous `col-main` |

## Showcase

`/app/design` — `AppDesignSystemShowcase` :

- **114** modules historiques (sections 01–11)
- **41** composants Webapp4 (sections 12–15)
- **6** patterns Webapp-full (section 16, iframes `160–165`)
- **5** composants React live (section 16b)

Sync : `node scripts/sync-webapp-full-design-system.mjs "/chemin/Webapp-full.zip"`

## Composants React (Webapp-full)

| Classe CSS | Composant | Usage |
|---|---|---|
| `.avt--safran` | `AppAccountDot` | Pastilles compte (cryptos, etc.) |
| `.brw-cta` | `AppBorrowCtaCard` | CTA avance de liquidité |
| `.brw` / `.brw-intro` / `.brw-dial` | `PortalLombardBorrowIntro`, `PortalLombardBorrowForm`, `PortalLombardRiskDial` | Flux emprunt Lombard (`/app/borrow`) — CSS `borrow-flow.css` |
| `.loan` | `AppLoanCard` | Carte emprunt actif (Lombard / Morpho) |
| `.mstick` | `AppMobileStickyBar` | Barre CTA fixe mobile |
| `.actu-card` zoom | `AppActuCard` | Zoom image 1.05 au survol |

## Composants React portail (existants)

| DS / preview | Composant | Usage portail |
|---|---|---|
| `card-simple` / `tx-list` | `AppSurfaceCard`, `AppDataList`, `AppTxList` | Cartes blanches, listes |
| `17-list-transactions` | `AppTxRow`, `PortalTransactionHistory` | Historique crypto / épargne |
| `05-lists` stacked | `AppDataList` + classes `list__*` | My accounts, positions |
| `83-settings-list-row` | `AppSettingsList`, `AppSettingsRow` | Profil, Markets |
| `18-banners` | `AppBanner` | Bannière unlock EUR |
| `sh-app` | `AppSectionHeader` | Titres de modules in-page |
| `02-buttons` | `AppButton` | CTAs DS pill |

## Référence zip

Source : `Webapp-full.zip` → `design_handoff_vancelian/` (README, `vancelian.css`, vues `*.jsx`).

**Prototype statique local (gitignored)** : `.ds-handoff/design_handoff_vancelian/` — entrées `*.html`, vues `*-view.jsx`, JS précompilé `js/`. Copier depuis `~/Downloads/design_handoff_vancelian` puis `node scripts/build-ds-handoff-static.mjs` (obligatoire pour ouverture `file://` — voir `PREVIEW_LOCAL.md`).
