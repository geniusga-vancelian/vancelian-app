# Design System — Webapp (portail `/app/*`)

> Handoff **App Vancelian.zip** (mai 2026) — mobile-first, pixel-aligned sur `ui_kits/vancelian-app/`.

Le **site marketing** conserve son DS dans `vancelian-tokens.css` ; il n’est **pas** modifié par ce pack.

## Activation

Le layout racine pose `data-v-ds="app"` sur `<body>` pour toutes les routes `/app/*` (voir `src/app/layout.tsx`).

Les variables `--v-*` et les classes composants (`.btn`, `.card-simple`, `.v-eyebrow`, …) ne s’appliquent qu’à ce scope.

## Fichiers

| Fichier | Rôle |
|---|---|
| `src/styles/app/vancelian-app-tokens.css` | Tokens + typo sémantique (handoff `colors_and_type.css` v1.2) |
| `src/styles/app/vancelian-app-components.css` | Boutons, forms, cartes, nav, … (`ui_kits/vancelian-app/styles/*`) |
| `src/styles/app/design-system-app-theme.css` | Pont shadcn (cartes blanches, warning safran) |
| `src/components/design-system/app/*` | Wrappers React (`AppEyebrow`, `AppButton`, `AppCard`, …) |
| `src/components/design-system/app/tokens.ts` | Hex statiques pour charts / SVG |

## Différences clés vs website

| Règle | Website | Webapp |
|---|---|---|
| Carte produit | `#F2F1ED` (`--v-card`) | `#FFFFFF` (`.card-simple`) |
| Warning | Terracotta | Safran `#C99A2E` |
| Eyebrow | 11px / 0.05em | 13px / 0.08em / 600 (`.v-eyebrow`) |
| Radius max | 16 / 20 / 24 marketing | 12 px (+ pill, sheet 24) |
| Newsreader | Sections marketing | Balance card, onboarding uniquement |

## Showcase

`/app/design` — `AppDesignSystemShowcase` : **114 modules** en iframes (`public/app-ds/preview/*.html`), structure App Vancelian v2.2 + Webapp3 (sections 09–11 : primitives · shell · patterns produit).

## Composants React portail (wrappers)

| DS / preview | Composant | Usage portail |
|---|---|---|
| `card-simple` / `tx-list` | `AppSurfaceCard`, `AppDataList`, `AppTxList` | Cartes blanches, listes |
| `17-list-transactions` | `AppTxRow`, `PortalTransactionHistory` | Historique crypto / épargne |
| `05-lists` stacked | `AppDataList` + classes `list__*` | My accounts, positions |
| `83-settings-list-row` | `AppSettingsList`, `AppSettingsRow` | Profil, Markets (top crypto) |
| `18-banners` | `AppBanner` | Bannière unlock EUR |
| `sh-app` | `AppSectionHeader` | Titres de modules in-page |
| `02-buttons` | `AppButton` | CTAs DS pill (showcase + à généraliser) |

## Référence zip

Bundle local extrait sous `.ds-handoff/` (gitignored via usage dev) — source : `App Vancelian.zip`.
