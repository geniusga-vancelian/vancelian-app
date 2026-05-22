/**
 * Vancelian Design System — tokens TypeScript.
 *
 * Projection statique des variables CSS `--v-*` définies dans
 * `src/styles/vancelian-tokens.css`. À utiliser pour les composants qui
 * ont besoin de hex statiques (mock data, SVG, emails MJML, …).
 *
 * Source de vérité : pack handoff officiel (Claude Design) — README + colors_and_type.css.
 * Doctrine : premium discret · Aman / Hermès / Cereal.
 *
 * Pour le CSS / Tailwind, préférer toujours les variables CSS et les classes
 * exposées (`text-v-fg`, `bg-v-bg`, `text-v-terracotta`, etc.).
 */

export const vancelianColors = {
  // Surfaces — papier off-white, jamais blanc pur
  bg: '#F7F7F4',
  bgPhoto: '#F5F1EA',
  card: '#F2F1ED',
  cardWarm: '#F3EDE6',
  cardHover: '#EBEAE5',
  darkBg: '#141208',

  // Foregrounds — anthracite, jamais noir pur
  fg: '#1A1815',
  fgBody: '#3A352F',
  fgMuted: '#6E665C',
  fgLight: '#8E867A',
  fg20: '#C9C3B5',
  fg10: '#E2DED4',
  fg05: '#EFEDE6',
  darkFg: '#EDECEC',

  // Triade chromatique identitaire — jamais simultanée en aplat
  terracotta: '#C0512E',
  terracottaPressed: '#A0431C',
  green: '#33614D',
  blue: '#0F2A47',

  // Sémantiques
  success: '#33614D',
  warning: '#C0512E',
  info: '#0F2A47',
  error: '#B83A3A',

  // Gris technique (neutres)
  gray50: '#F9FAFB',
  gray200: '#E5E7EB',
  gray300: '#D1D5DC',
  gray500: '#6A7282',
  gray700: '#364153',
  gray900: '#101828',
} as const

export const vancelianFonts = {
  ui: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
  editorial: '"Newsreader", "Iowan Old Style", Georgia, serif',
  display: '"Newsreader Display", "Newsreader", Georgia, serif',
} as const

export const vancelianWeights = {
  light: 300,
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const

/** Échelle d'espacement Vancelian — 8 paliers stricts (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64). */
export const vancelianSpacing = {
  none: 0,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
  '4xl': 64,
} as const

/** Échelle de radius Vancelian — 5 paliers stricts (+ 3 alias marketing). */
export const vancelianRadius = {
  none: 0,
  tag: 4,
  input: 6,
  card: 8,
  modal: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  pill: 999,
} as const

/** Élévations — 3 niveaux seulement. */
export const vancelianShadows = {
  flat: 'none',
  subtle: '0 1px 2px 0 rgba(26, 24, 21, 0.04)',
  medium: '0 8px 24px 0 rgba(26, 24, 21, 0.08)',
} as const

/** Motion — discret, court, naturel. */
export const vancelianMotion = {
  fast: '120ms',
  base: '200ms',
  slow: '320ms',
  easeOut: 'cubic-bezier(0.22, 1, 0.36, 1)',
  easeInOut: 'cubic-bezier(0.65, 0, 0.35, 1)',
} as const

export type VancelianColorToken = keyof typeof vancelianColors
export type VancelianSpacingToken = keyof typeof vancelianSpacing
export type VancelianRadiusToken = keyof typeof vancelianRadius
