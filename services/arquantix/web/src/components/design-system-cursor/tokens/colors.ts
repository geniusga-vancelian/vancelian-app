/**
 * Design System "Cursor" — Tokens couleurs
 *
 * Source : extraction depuis https://cursor.com/get-started
 * (CSS bundles `_next/static/chunks/*.css`, dépôt dpl_7mc8HHaAAo4pCH5aNueGuefkyUEe).
 *
 * Convention de nommage : on conserve les noms d'origine de Cursor
 * (`color-theme-*`, `color-theme-fg-*`, etc.) pour rester traçable.
 *
 * Les valeurs hex avec un canal alpha (`#RRGGBBAA`) sont conservées telles
 * quelles ; certains outils n'aiment pas l'alpha hex, on les rend donc
 * également via une string CSS qui sera appliquée en `background-color`.
 */

export type CursorColorToken = {
  /** Nom canonique sans le préfixe `--` (ex: `color-theme-bg`). */
  name: string
  /** Valeur CSS exacte (ex: `#f7f7f4`, `#26251e1a`, …). */
  value: string
  /** Étiquette courte humaine (ex: `Background`). */
  label: string
  /** Description optionnelle (rôle, usage). */
  description?: string
}

export type CursorColorGroup = {
  id: string
  title: string
  description?: string
  tokens: CursorColorToken[]
}

/* -------------------------------------------------------------------------- */
/*  THEME — LIGHT (palette par défaut sur cursor.com)                         */
/* -------------------------------------------------------------------------- */

export const themeLight: CursorColorGroup = {
  id: 'theme-light',
  title: 'Theme — Light',
  description:
    'Palette principale visible par défaut sur cursor.com (mode clair). Chaude, papier off-white, foreground anthracite.',
  tokens: [
    {
      name: 'color-theme-bg',
      value: '#f7f7f4',
      label: 'Background',
      description: 'Fond principal de la page.',
    },
    {
      name: 'color-theme-fg',
      value: '#26251e',
      label: 'Foreground',
      description: 'Couleur de texte principale, encres et icônes.',
    },
    {
      name: 'color-theme-fg-02',
      value: '#3b3a33',
      label: 'Foreground 02',
      description: 'Variante hover du foreground (boutons primaires).',
    },
    {
      name: 'color-theme-accent',
      value: '#f54e00',
      label: 'Accent',
      description: 'Orange Cursor — accent unique de la marque.',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  THEME — DARK (overrides via [data-theme="dark"])                          */
/* -------------------------------------------------------------------------- */

export const themeDark: CursorColorGroup = {
  id: 'theme-dark',
  title: 'Theme — Dark',
  description:
    'Overrides activés via `[data-theme="dark"]`. Fonds très sombres légèrement chauds, foreground crème.',
  tokens: [
    {
      name: 'color-theme-bg (dark)',
      value: '#14120b',
      label: 'Background',
      description: 'Fond principal en mode sombre.',
    },
    {
      name: 'color-theme-fg (dark)',
      value: '#edecec',
      label: 'Foreground',
      description: 'Couleur texte principale en mode sombre.',
    },
    {
      name: 'color-theme-fg-02 (dark)',
      value: '#d7d6d5',
      label: 'Foreground 02',
      description: 'Variante hover du foreground.',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  FOREGROUND — opacités appliquées sur fg (#26251e + alpha)                  */
/* -------------------------------------------------------------------------- */

export const foregroundScale: CursorColorGroup = {
  id: 'fg-scale',
  title: 'Foreground — échelle d’opacité',
  description:
    'Variations alpha de `--color-theme-fg` (#26251e). Utilisées pour overlays, séparateurs et états désactivés.',
  tokens: [
    { name: 'color-theme-fg-01', value: '#26251e03', label: 'fg / 1%' },
    { name: 'color-theme-fg-02-5', value: '#26251e06', label: 'fg / 2.5%' },
    { name: 'color-theme-fg-05', value: '#26251e0d', label: 'fg / 5%' },
    { name: 'color-theme-fg-07-5', value: '#26251e13', label: 'fg / 7.5%' },
    { name: 'color-theme-fg-10', value: '#26251e1a', label: 'fg / 10%' },
    { name: 'color-theme-fg-15', value: '#26251e26', label: 'fg / 15%' },
    { name: 'color-theme-fg-20', value: '#26251e33', label: 'fg / 20%' },
  ],
}

/* -------------------------------------------------------------------------- */
/*  BORDERS                                                                   */
/* -------------------------------------------------------------------------- */

export const borders: CursorColorGroup = {
  id: 'borders',
  title: 'Borders',
  description:
    'Bordures alpha sur fond clair. `border-01` est le plus léger (séparateur discret), `border-03` le plus marqué (boutons secondaires).',
  tokens: [
    {
      name: 'color-theme-border-01',
      value: '#26251e06',
      label: 'Border 01',
      description: 'Séparateurs discrets (≈ 2.5% alpha).',
    },
    {
      name: 'color-theme-border-01-5',
      value: '#26251e0d',
      label: 'Border 01.5',
      description: '≈ 5% alpha.',
    },
    {
      name: 'color-theme-border-02',
      value: '#26251e1a',
      label: 'Border 02',
      description: 'Bordure standard (cartes, inputs).',
    },
    {
      name: 'color-theme-border-02-5',
      value: '#26251e33',
      label: 'Border 02.5',
      description: 'Bordure renforcée (focus, hover).',
    },
    {
      name: 'color-theme-border-03',
      value: '#26251e99',
      label: 'Border 03',
      description: 'Bordure forte (boutons secondaires, info).',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  CARDS                                                                     */
/* -------------------------------------------------------------------------- */

export const cardsLight: CursorColorGroup = {
  id: 'cards-light',
  title: 'Cards — Light',
  description:
    'Variations de fonds pour cartes et surfaces empilées (du plus clair au plus profond).',
  tokens: [
    { name: 'color-theme-card-hex', value: '#f2f1ed', label: 'Card (base)' },
    { name: 'color-theme-card-01-hex', value: '#f0efeb', label: 'Card 01' },
    { name: 'color-theme-card-02-hex', value: '#ebeae5', label: 'Card 02' },
    { name: 'color-theme-card-03-hex', value: '#e6e5e0', label: 'Card 03' },
    { name: 'color-theme-card-04-hex', value: '#e1e0db', label: 'Card 04' },
    {
      name: 'color-theme-card-hover-hex',
      value: '#ebeae5',
      label: 'Card hover',
    },
    {
      name: 'color-theme-card-hover-light-hex',
      value: '#f0efeb',
      label: 'Card hover light',
    },
    {
      name: 'color-theme-card-warm-hex',
      value: '#f3ede6',
      label: 'Card warm',
      description: 'Variante chaude (testimonials, blocs marketing).',
    },
  ],
}

export const cardsDark: CursorColorGroup = {
  id: 'cards-dark',
  title: 'Cards — Dark',
  description: 'Surfaces empilées en mode sombre.',
  tokens: [
    { name: 'color-theme-card-hex (dark)', value: '#1b1913', label: 'Card (base)' },
    { name: 'color-theme-card-01-hex (dark)', value: '#1d1b15', label: 'Card 01' },
    { name: 'color-theme-card-02-hex (dark)', value: '#201e18', label: 'Card 02' },
    { name: 'color-theme-card-03-hex (dark)', value: '#26241e', label: 'Card 03' },
    { name: 'color-theme-card-04-hex (dark)', value: '#2b2923', label: 'Card 04' },
    { name: 'color-theme-card-hover-hex (dark)', value: '#201e18', label: 'Card hover' },
    {
      name: 'color-theme-card-hover-light-hex (dark)',
      value: '#1d1b15',
      label: 'Card hover light',
    },
    { name: 'color-theme-card-warm-hex (dark)', value: '#1c1713', label: 'Card warm' },
  ],
}

/* -------------------------------------------------------------------------- */
/*  TEXT                                                                      */
/* -------------------------------------------------------------------------- */

export const text: CursorColorGroup = {
  id: 'text',
  title: 'Text',
  description:
    'Hiérarchie typographique. `text` reprend `fg`, `text-mid` ≈ 50%, `text-sec` ≈ 60%, `text-tertiary` ≈ 40%.',
  tokens: [
    {
      name: 'color-theme-text',
      value: '#26251e',
      label: 'Text (primary)',
      description: 'Identique à `fg`.',
    },
    {
      name: 'color-theme-text-mid',
      value: '#26251e80',
      label: 'Text mid (~50%)',
    },
    {
      name: 'color-theme-text-sec',
      value: '#26251e99',
      label: 'Text secondary (~60%)',
    },
    {
      name: 'color-theme-text-tertiary',
      value: '#26251e66',
      label: 'Text tertiary (~40%)',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  PRODUCT (mockups éditeur, ANSI, diff lines)                               */
/* -------------------------------------------------------------------------- */

export const product: CursorColorGroup = {
  id: 'product',
  title: 'Product (éditeur)',
  description:
    'Couleurs des mockups de l’IDE Cursor : chrome, éditeur, texte produit, ANSI, lignes diff.',
  tokens: [
    {
      name: 'color-theme-product-chrome',
      value: '#f2f1ed',
      label: 'Chrome',
      description: 'Sidebar / header de l’éditeur (alias de Card light).',
    },
    {
      name: 'color-theme-product-editor',
      value: '#f7f7f4',
      label: 'Editor',
      description: 'Surface du buffer de code (alias de bg light).',
    },
    {
      name: 'color-theme-product-text',
      value: '#26251eeb',
      label: 'Product text (~92%)',
    },
    {
      name: 'color-theme-product-text-sec',
      value: '#26251e99',
      label: 'Product text sec (~60%)',
    },
    {
      name: 'color-theme-product-text-tertiary',
      value: '#26251e66',
      label: 'Product text tertiary (~40%)',
    },
    {
      name: 'color-theme-product-ansi-green',
      value: '#1f8a65',
      label: 'ANSI green',
      description: 'Succès terminal, lignes ajoutées.',
    },
    {
      name: 'color-theme-product-ansi-red',
      value: '#cf2d56',
      label: 'ANSI red',
      description: 'Erreurs terminal, lignes supprimées.',
    },
    {
      name: 'color-theme-product-line-inserted-line-background',
      value: '#1f8a6514',
      label: 'Inserted line bg',
      description: 'Surlignage des lignes ajoutées (~8% alpha).',
    },
    {
      name: 'color-theme-product-removed-line-background',
      value: '#cf2d560f',
      label: 'Removed line bg',
      description: 'Surlignage des lignes supprimées (~6% alpha).',
    },
  ],
}

/* -------------------------------------------------------------------------- */
/*  TIMELINE (UI agent — types d’actions)                                     */
/* -------------------------------------------------------------------------- */

export const timeline: CursorColorGroup = {
  id: 'timeline',
  title: 'Timeline (agent)',
  description:
    'Couleurs pastel pour la timeline d’actions de l’agent (lecture, édition, recherche, réflexion).',
  tokens: [
    { name: 'color-timeline-edit', value: '#c0a8dd', label: 'Edit' },
    { name: 'color-timeline-grep', value: '#9fc9a2', label: 'Grep' },
    { name: 'color-timeline-read', value: '#9fbbe0', label: 'Read' },
    { name: 'color-timeline-thinking', value: '#dfa88f', label: 'Thinking' },
  ],
}

/* -------------------------------------------------------------------------- */
/*  SEMANTIC (success / error / warning / info)                               */
/* -------------------------------------------------------------------------- */

export const semantic: CursorColorGroup = {
  id: 'semantic',
  title: 'Semantic',
  description:
    'Sémantique d’état. Rappels résolus à partir des autres tokens (les `*-bg` sont des color-mix à 15% sur transparent).',
  tokens: [
    { name: 'color-success', value: '#1f8a65', label: 'Success', description: 'Alias ANSI green.' },
    { name: 'color-success-bg', value: '#1f8a6526', label: 'Success bg (~15%)' },
    { name: 'color-error', value: '#cf2d56', label: 'Error', description: 'Alias ANSI red.' },
    { name: 'color-error-bg', value: '#cf2d5626', label: 'Error bg (~15%)' },
    { name: 'color-warning', value: '#f54e00', label: 'Warning', description: 'Alias accent orange.' },
    { name: 'color-warning-bg', value: '#f54e0026', label: 'Warning bg (~15%)' },
    { name: 'color-info', value: '#26251e99', label: 'Info', description: 'Alias border-03.' },
    { name: 'color-accent-bg', value: '#f54e001a', label: 'Accent bg (~10%)' },
    { name: 'color-accent-bg-strong', value: '#f54e0040', label: 'Accent bg strong (~25%)' },
  ],
}

/* -------------------------------------------------------------------------- */
/*  PALETTE (Tailwind v4 default — réutilisée dans le bundle)                 */
/* -------------------------------------------------------------------------- */

export const grayPalette: CursorColorGroup = {
  id: 'palette-gray',
  title: 'Gray (Tailwind)',
  description: 'Échelle de gris (Tailwind v4) embarquée dans le bundle Cursor.',
  tokens: [
    { name: 'color-gray-50', value: '#f9fafb', label: '50' },
    { name: 'color-gray-200', value: '#e5e7eb', label: '200' },
    { name: 'color-gray-300', value: '#d1d5dc', label: '300' },
    { name: 'color-gray-500', value: '#6a7282', label: '500' },
    { name: 'color-gray-600', value: '#4a5565', label: '600' },
    { name: 'color-gray-700', value: '#364153', label: '700' },
    { name: 'color-gray-800', value: '#1e2939', label: '800' },
    { name: 'color-gray-900', value: '#101828', label: '900' },
  ],
}

export const accentPalette: CursorColorGroup = {
  id: 'palette-accent',
  title: 'Accent palette',
  description: 'Couleurs accents secondaires utilisées ponctuellement (Tailwind v4).',
  tokens: [
    { name: 'color-blue-50', value: '#eff6ff', label: 'Blue 50' },
    { name: 'color-blue-600', value: '#155dfc', label: 'Blue 600' },
    { name: 'color-blue-800', value: '#193cb8', label: 'Blue 800' },
    { name: 'color-blue-900', value: '#1c398e', label: 'Blue 900' },
    { name: 'color-green-50', value: '#f0fdf4', label: 'Green 50' },
    { name: 'color-green-500', value: '#00c758', label: 'Green 500' },
    { name: 'color-green-600', value: '#00a544', label: 'Green 600' },
    { name: 'color-green-800', value: '#016630', label: 'Green 800' },
    { name: 'color-green-900', value: '#0d542b', label: 'Green 900' },
    { name: 'color-red-500', value: '#fb2c36', label: 'Red 500' },
    { name: 'color-red-600', value: '#e40014', label: 'Red 600' },
    { name: 'color-purple-400', value: '#c07eff', label: 'Purple 400' },
    { name: 'color-slate-200', value: '#e2e8f0', label: 'Slate 200' },
    { name: 'color-slate-500', value: '#62748e', label: 'Slate 500' },
  ],
}

export const baseNeutrals: CursorColorGroup = {
  id: 'palette-base',
  title: 'Base',
  description: 'Noir et blanc absolus.',
  tokens: [
    { name: 'color-black', value: '#000000', label: 'Black' },
    { name: 'color-white', value: '#ffffff', label: 'White' },
  ],
}

/* -------------------------------------------------------------------------- */
/*  EXPORT                                                                    */
/* -------------------------------------------------------------------------- */

/** Tous les groupes, dans l’ordre d’affichage de la page de visualisation. */
export const cursorColorGroups: CursorColorGroup[] = [
  themeLight,
  themeDark,
  foregroundScale,
  borders,
  cardsLight,
  cardsDark,
  text,
  product,
  timeline,
  semantic,
  grayPalette,
  accentPalette,
  baseNeutrals,
]
