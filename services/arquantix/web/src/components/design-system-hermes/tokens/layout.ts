/**
 * Design System "Hermès" — Layout & élévation
 *
 * Source : `hermes.ef2936e76bedc435.css` + JSON tokens du bundle
 * `main.03131fe7703be59e.js` (https://www.hermes.com/fr/fr/).
 */

export type HermesLayoutToken = {
  name: string
  value: string
  label: string
  description?: string
}

/* -------------------------------------------------------------------------- */
/*  BREAKPOINTS                                                                */
/* -------------------------------------------------------------------------- */

export const hermesBreakpoints: HermesLayoutToken[] = [
  {
    name: 'smallest',
    value: '320px',
    label: 'Smallest',
    description: 'Borne basse mobile (iPhone SE 1ʳᵉ génération).',
  },
  {
    name: 'desktop',
    value: '1024px',
    label: 'Desktop',
    description: 'Bascule layout mobile → desktop.',
  },
  {
    name: 'desktop-large',
    value: '1920px',
    label: 'Desktop large',
    description: 'Affichage grand écran (4K, vitrines).',
  },
]

/* -------------------------------------------------------------------------- */
/*  HEADER                                                                     */
/* -------------------------------------------------------------------------- */

export const hermesHeaderHeights: HermesLayoutToken[] = [
  {
    name: '--header-height-mobile',
    value: '50px',
    label: 'Header — Mobile',
    description: 'Hauteur header sur mobile (logo H + burger).',
  },
  {
    name: '--header-height-desktop',
    value: '64px',
    label: 'Header — Desktop',
    description: 'Hauteur header desktop, sans menu déroulé.',
  },
  {
    name: '--header-height-desktop-with-menu',
    value: '110px',
    label: 'Header — Desktop + menu',
    description: 'Hauteur header desktop avec barre de catégories étendue.',
  },
  {
    name: '--header-menu-top',
    value: '58px',
    label: 'Header — Menu top',
    description: 'Décalage du menu burger (iOS only).',
  },
]

/* -------------------------------------------------------------------------- */
/*  GUTTERS / MARGES (3 layouts : adaptive, narrow, fixe)                      */
/* -------------------------------------------------------------------------- */

export const hermesLayoutGutters: HermesLayoutToken[] = [
  {
    name: 'layout-type-margin-adaptative',
    value: '24px',
    label: 'Adaptative — desktop',
    description: 'Gouttière par défaut sur desktop (24px de chaque côté).',
  },
  {
    name: 'layout-type-margin-adaptative-max-width',
    value: '1258px',
    label: 'Adaptative — max width',
    description: 'Largeur max d’un container adaptative.',
  },
  {
    name: 'layout-type-margin-adaptative-mobile',
    value: '15px',
    label: 'Adaptative — mobile',
    description: 'Gouttière mobile.',
  },
  {
    name: 'layout-type-margin-narrow-max-width',
    value: '976px',
    label: 'Narrow — max width',
    description: 'Largeur max pour les pages éditoriales (lecture confort).',
  },
  {
    name: 'layout-type-margin-narrow-mobile',
    value: '15px',
    label: 'Narrow — mobile',
    description: 'Mobile : même gouttière que adaptive.',
  },
  {
    name: 'layout-type-margin-fixe-mobile',
    value: '4px',
    label: 'Fixe — mobile',
    description: 'Gouttière minimale (carrousels plein bord).',
  },
  {
    name: 'layout-type-margin-fixe-desktop',
    value: '24px',
    label: 'Fixe — desktop',
    description: 'Gouttière fixe desktop.',
  },
]

/* -------------------------------------------------------------------------- */
/*  Z-INDEX (l’élévation)                                                      */
/* -------------------------------------------------------------------------- */

export const hermesZIndex: HermesLayoutToken[] = [
  {
    name: 'z-baidu-suggestion',
    value: '90',
    label: 'Z — Baidu suggestion',
    description: 'Suggestions inline (marché Chine).',
  },
  {
    name: 'z-header',
    value: '300',
    label: 'Z — Header',
    description: 'Barre de navigation principale.',
  },
  {
    name: 'z-livechat',
    value: '999',
    label: 'Z — Livechat',
    description: 'Bulle de support live (Salesforce).',
  },
  {
    name: 'z-baidu-suggestion-tray',
    value: '2010',
    label: 'Z — Baidu suggestion tray',
    description: 'Plateau Baidu au-dessus de tout.',
  },
]
