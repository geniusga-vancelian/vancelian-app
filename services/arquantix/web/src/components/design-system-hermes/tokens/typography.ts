/**
 * Design System "Hermès" — Tokens typographiques
 *
 * Source : extraction depuis `hermes.ef2936e76bedc435.css` et le bundle
 * `main.03131fe7703be59e.js` (https://www.hermes.com/fr/fr/).
 *
 * Hermès expose plusieurs *familles* :
 *   - **font-primary** : Manrope (sans-serif courant, UI, navigation).
 *   - **font-secondary** : Overpass Mono (monospace, légendes, prix).
 *   - **font-edito** : EB Garamond (serif éditorial, titres luxe).
 *   - **fontes vedettes** (display) : Filosofia, Akkurat, Jungle Love,
 *     Brides de Gala, Mors à Jouet — utilisées sur les pages campagne.
 *
 * Pour chaque famille, Hermès définit deux échelles parallèles :
 *   - **heading** (xxl → xs) : titres
 *   - **body**    (xl  → xs) : paragraphes / UI
 * + 8 graisses (`100` → `800`).
 */

export type HermesFontToken = {
  name: string
  /** Stack CSS complet. */
  stack: string
  /** Étiquette courte. */
  label: string
  /** Rôle / usage. */
  role: string
  /** Aperçu personnalisé. */
  sample?: string
  /** Famille principale (pour le pangramme dans la prévisu). */
  family?: string
}

export type HermesFontSizeToken = {
  name: string
  value: string
  label: string
  /** Pixels équivalents (16px = 1rem). */
  px: number
  description?: string
}

export type HermesFontWeightToken = {
  name: string
  value: number
  label: string
}

/* -------------------------------------------------------------------------- */
/*  FAMILLES (3 familles principales + 5 polices vedettes)                    */
/* -------------------------------------------------------------------------- */

export const hermesFontFamilies: HermesFontToken[] = [
  {
    name: 'font-primary',
    label: 'Primary — Manrope',
    role: 'Sans-serif courant. UI, navigation, paragraphes courts.',
    stack: '"Manrope", "Roboto", sans-serif',
    family: 'Manrope',
  },
  {
    name: 'font-secondary',
    label: 'Secondary — Overpass Mono',
    role: 'Monospace. Prix, métadonnées, références produit.',
    stack: '"Overpass Mono", "Gill Sans MT", calibri, sans-serif',
    family: 'Overpass Mono',
  },
  {
    name: 'font-edito',
    label: 'Editorial — EB Garamond',
    role: 'Serif éditorial. Titres d’histoires, articles, hero.',
    stack: '"EBGaramond", "Bell MT", "Times New Roman", sans-serif',
    family: 'EB Garamond',
  },
  {
    name: 'font-filosofia',
    label: 'Display — Filosofia',
    role: 'Serif vedette. Affiches campagne, citations.',
    stack: '"Filosofia", serif',
    family: 'Filosofia',
  },
  {
    name: 'font-akkurat',
    label: 'Display — Akkurat',
    role: 'Sans-serif suisse. Mise en valeur des collections « objets ».',
    stack: '"Akkurat", serif',
    family: 'Akkurat',
  },
  {
    name: 'font-jungle-love',
    label: 'Display — Jungle Love',
    role: 'Script. Pages saisonnières « Jungle ».',
    stack: '"Jungle-Regular", serif',
    family: 'Jungle',
  },
  {
    name: 'font-brides-de-gala',
    label: 'Display — Brides de Gala',
    role: 'Display ornementé. Soieries, carrés et iconique « Brides de Gala ».',
    stack: '"BridesdeGala-Regular", serif',
    family: 'BridesdeGala',
  },
  {
    name: 'font-mors-a-jouet',
    label: 'Display — Mors à Jouet',
    role: 'Display équestre. Sellerie & maroquinerie.',
    stack: '"Mors-Regular-Auto", serif',
    family: 'Mors',
  },
]

/* -------------------------------------------------------------------------- */
/*  TAILLES — HEADING (titres)                                                */
/* -------------------------------------------------------------------------- */

export const hermesHeadingSizes: HermesFontSizeToken[] = [
  {
    name: 'font-size-heading-xxl',
    value: '2.125rem',
    label: 'Heading XXL',
    px: 34,
    description: 'Hero (default desktop). Mobile : 1.875rem.',
  },
  {
    name: 'font-size-heading-xl',
    value: '1.875rem',
    label: 'Heading XL',
    px: 30,
    description: 'Sections principales (default desktop).',
  },
  {
    name: 'font-size-heading-l',
    value: '1.625rem',
    label: 'Heading L',
    px: 26,
    description: 'Sous-sections.',
  },
  {
    name: 'font-size-heading-m',
    value: '1.5rem',
    label: 'Heading M',
    px: 24,
    description: 'Cartes & blocs marketing.',
  },
  {
    name: 'font-size-heading-default',
    value: '1.375rem',
    label: 'Heading default',
    px: 22,
    description: 'Titre par défaut.',
  },
  {
    name: 'font-size-heading-s',
    value: '1.25rem',
    label: 'Heading S',
    px: 20,
    description: 'Petits titres internes.',
  },
  {
    name: 'font-size-heading-xs',
    value: '1.125rem',
    label: 'Heading XS',
    px: 18,
    description: 'Mini titres (cartes produit).',
  },
]

/* -------------------------------------------------------------------------- */
/*  TAILLES — BODY (paragraphes & UI)                                          */
/* -------------------------------------------------------------------------- */

export const hermesBodySizes: HermesFontSizeToken[] = [
  {
    name: 'font-size-body-xl',
    value: '1rem',
    label: 'Body XL',
    px: 16,
    description: 'Lead paragraph.',
  },
  {
    name: 'font-size-body-l',
    value: '0.875rem',
    label: 'Body L',
    px: 14,
    description: 'Texte courant.',
  },
  {
    name: 'font-size-body-m',
    value: '0.75rem',
    label: 'Body M',
    px: 12,
    description: 'Caption, label.',
  },
  {
    name: 'font-size-body-default',
    value: '0.6875rem',
    label: 'Body default',
    px: 11,
    description: 'Texte par défaut UI.',
  },
  {
    name: 'font-size-body-s',
    value: '0.625rem',
    label: 'Body S',
    px: 10,
    description: 'Mentions légales courtes.',
  },
  {
    name: 'font-size-body-xs',
    value: '0.5rem',
    label: 'Body XS',
    px: 8,
    description: 'Footnotes, copyrights.',
  },
]

/* -------------------------------------------------------------------------- */
/*  GRAISSES                                                                   */
/* -------------------------------------------------------------------------- */

export const hermesFontWeights: HermesFontWeightToken[] = [
  { name: 'font-weight-100', value: 100, label: 'Thin' },
  { name: 'font-weight-200', value: 200, label: 'Extra Light' },
  { name: 'font-weight-300', value: 300, label: 'Light' },
  { name: 'font-weight-400', value: 400, label: 'Regular' },
  { name: 'font-weight-500', value: 500, label: 'Medium' },
  { name: 'font-weight-600', value: 600, label: 'Semi Bold' },
  { name: 'font-weight-700', value: 700, label: 'Bold' },
  { name: 'font-weight-800', value: 800, label: 'Extra Bold' },
]

/* -------------------------------------------------------------------------- */
/*  LETTER-SPACING                                                             */
/* -------------------------------------------------------------------------- */

export const hermesLetterSpacings = [
  { name: 'letter-spacing-one', value: '1px', label: 'One — 1px' },
  { name: 'letter-spacing-half', value: '0.5px', label: 'Half — 0.5px' },
  { name: 'no-letter-spacing', value: '0', label: 'None — 0' },
]
