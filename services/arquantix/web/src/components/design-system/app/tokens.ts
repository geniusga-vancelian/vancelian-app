/**
 * Vancelian **App** Design System — tokens TypeScript.
 *
 * Projection des variables `--v-*` sous `[data-v-ds="app"]`
 * (`src/styles/app/vancelian-app-tokens.css`).
 * Source : handoff `App Vancelian.zip` — `colors_and_type.css` v1.2.
 */

export const vancelianAppColors = {
  bg: '#F7F7F4',
  bgPhoto: '#F5F1EA',
  card: '#F2F1ED',
  cardWarm: '#F3EDE6',
  cardHover: '#EBEAE5',
  darkBg: '#141208',
  white: '#FFFFFF',

  fg: '#1A1815',
  fgBody: '#3A352F',
  fgMuted: '#6E665C',
  fgLight: '#8E867A',
  fg20: '#C9C3B5',
  fg10: '#E2DED4',
  fg05: '#EFEDE6',
  fgHover: '#3B3633',
  darkFg: '#EDECEC',

  inputBorder: '#D9D4CC',
  inputDisabledBg: '#E8E4DD',
  inputDisabledBorder: '#DAD5CB',

  terracotta: '#C0512E',
  terracottaPressed: '#A0431C',
  green: '#33614D',
  blue: '#0F2A47',
  yellow: '#C99A2E',
  yellowPressed: '#A37D1F',

  success: '#33614D',
  warning: '#C99A2E',
  info: '#0F2A47',
  error: '#B83A3A',

  terracottaOnDark: '#E5896E',
  greenOnDark: '#8FC9A8',
  blueOnDark: '#8FB4D8',
  yellowOnDark: '#E8C778',
  errorOnDark: '#E89090',
} as const

export const vancelianAppRadius = {
  tag: 4,
  input: 6,
  card: 8,
  modal: 12,
  sheet: 24,
  pill: 9999,
} as const

export const vancelianAppSpacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
  '4xl': 64,
} as const
