# Design System — Vancelian (site web)

> *Là où l'argent travaille.*

> **Séparation webapp / website** — le portail `/app/*` a son propre DS : voir [`APP_DESIGN_SYSTEM.md`](./APP_DESIGN_SYSTEM.md). Ce fichier documente **uniquement le site marketing**.

Le site web Arquantix utilise le **Design System Vancelian Website** (handoff site / home.zip — figé).

Source de vérité :
- **CSS** : `src/styles/vancelian-tokens.css` (tokens `--v-*` + `@font-face` Inter / Newsreader + classes utilitaires sémantiques).
- **TypeScript** : `src/components/design-system/vancelian/tokens.ts` (projection statique des hex pour mock data / SVG / emails).
- **Tailwind** : `tailwind.config.ts` expose toute la palette via les classes `bg-v-*`, `text-v-*`, `border-v-*`, `rounded-v-*`, `shadow-v-*`, `font-ui`, `font-editorial`, `font-display`, `duration-v-*`, etc.

Le mapping `shadcn → Vancelian` est défini dans `src/styles/design-system-theme.css` : les anciennes variables `--primary`, `--background`, `--card`, `--muted`, `--destructive`, `--radius` héritent désormais des valeurs DS. Les composants shadcn existants (`Button`, `Card`, `Input`, …) **adoptent automatiquement** la nouvelle charte sans modification.

## Doctrine — règles inviolables

1. **Aucun bleu générique ni indigo.** Le seul bleu autorisé est `info #0F2A47` (bleu de Prusse).
2. **CTA primaire = anthracite `#1A1815`**, jamais terracotta. La terracotta `#C0512E` est réservée aux text-links et accents éditoriaux.
3. **Inter pour tout ce qui est cliquable ou fonctionnel.** **Newsreader pour la voix de marque** (titres éditoriaux, citations, wordmark). Jamais Newsreader sur un bouton ou un input.
4. **Wordmark VANCELIAN** : toujours Newsreader, uppercase, `letter-spacing: 0.4em`. Composant `<VancelianWordmark>` ou classe `.v-wordmark`.
5. **Espacement strict** : 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px. Pas de 14, 18, 20.
6. **Radius strict** : 4 (tag) / 6 (input) / 8 (card) / 12 (modal) / 999 (pill). + alias marketing : 16 / 20 / 24.
7. **Trois élévations seulement** : `flat` (none) / `subtle` / `medium`. Rien de plus lourd.
8. **Icônes Kalai uniquement** (mono, `currentColor`). Tailles 16 / 20 / 24 / 32. Voir `<KalaiIcon>`.
9. **Aucun emoji dans l'interface.** Aucun copy d'urgence / FOMO.
10. **Français d'abord, anglais ensuite.** Nombres `12 247,80 €`, pourcentages `+12,4 %`, dates « 12 mars 2026 ».

## Palette

| Token | Hex | Usage |
|---|---|---|
| `--v-bg` | `#F7F7F4` | Fond produit (papier off-white, jamais blanc pur) |
| `--v-card` | `#F2F1ED` | Carte niveau 1 |
| `--v-card-warm` | `#F3EDE6` | Carte warm — testimonials, marketing |
| `--v-fg` | `#1A1815` | Anthracite, jamais noir pur |
| `--v-fg-muted` | `#6E665C` | Texte secondaire |
| `--v-terracotta` | `#C0512E` | Text-links, accents éditoriaux, `warning` |
| `--v-green` | `#33614D` | Vert anglais — `success`, patrimoine |
| `--v-blue` | `#0F2A47` | Bleu de Prusse — `info`, institutionnel |
| `--v-error` | `#B83A3A` | Seul rouge, hors triade |
| `--v-dark-bg` | `#141208` | Dark mode / footer |
| `--v-dark-fg` | `#EDECEC` | Foreground sur fond dark |

## Composants atomiques

| Composant | Source |
|---|---|
| `<Button>` | `src/components/ui/button.tsx` — variants `default` (anthracite), `outline`, `secondary`, `ghost`, `link` (terracotta), `darkPrimary`, `darkSecondary`, `destructive` |
| `<Logo>` | `src/components/ui/Logo.tsx` — lockups horizontal / vertical / icon × noir / blanc (assets `public/brand/vancelian/`) |
| `<VancelianWordmark>` | Idem — wordmark texte Newsreader UPPERCASE 0.4em |
| `<KalaiIcon>` | `src/components/ui/KalaiIcon.tsx` — 473 icônes Kalai (mask-image + `currentColor`) |
| Classes utilitaires CSS | `.v-display` / `.v-h1..h4` / `.v-body` / `.v-caption` / `.v-eyebrow-section` / `.v-text-link` / `.v-tag--*` / `.v-card` / `.v-btn--*` |

## Chrome global

| Élément | Source |
|---|---|
| Navigation | `src/components/sections/Navigation.tsx` — barre fixe, palette anthracite / off-white, états transparent / scrolled. Logo via `<Logo lockup="horizontal" />`. |
| Footer | `src/components/design-system/Footer.tsx` (DS) + `src/components/sections/Footer.tsx` (adaptateur CMS). Fond `--v-dark-bg`, baseline Newsreader italic, titres colonnes en `.v-caption`, liens 13px medium. |
| Body root | `src/components/design-system/extracted/tokens/surfaces.ts` — `figmaDsBodyRootClassName = "min-h-screen bg-v-bg text-v-fg antialiased"`. |

## Couche héritée — DS Figma extraite (`extracted/`)

L'ancien DS Figma (préfixe `figmaDs*`) reste présent dans `extracted/` pour compatibilité ascendante. Ses **tokens couleurs ont été remappés** sur la palette Vancelian (`extracted/tokens/colors.ts` → off-white / anthracite). Les composants `extracted/atoms/*` n'utilisent plus Avenir (migration via mass-update Inter — voir commit). Cette couche sera supprimée progressivement au fur et à mesure de la migration des sections.

## Templates validés (4 archétypes DS)

1. **Hero éditorial** — home, marketing pages
2. **Dashboard** — espace authentifié
3. **List view** — catalogue, transactions
4. **Detail view** — token, profil

## Assets

| Asset | Chemin public |
|---|---|
| Fonts Newsreader (12 fichiers, 3 tailles optiques) | `public/fonts/newsreader/` |
| Lockups Vancelian (6 SVG + 4 PNG) | `public/brand/vancelian/` |
| Icônes Kalai (473 SVG) + index JSON | `public/icons/kalai/`, `public/icons/kalai.json` |

## Référence

Le bundle officiel (`Vancelian Design System-handoff`) est l'unique source de vérité visuelle. En cas de divergence entre la doc et le bundle, **le bundle gagne**.

## Flutter

Le design system mobile Flutter n'est pas défini ici ; ne pas confondre avec ces fichiers.
