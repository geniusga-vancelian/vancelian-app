/**
 * Design system **HTML e-mail** Arquantix — découplé du DS site (`components/design-system`, `figmaDs*`).
 * Utiliser uniquement des styles inline dans les composants ; pas de dépendance aux CSS globaux du site.
 */
export const emailDsColors = {
  black: '#000000',
  charcoal: '#272727',
  charcoal2: '#1C1C1C',
  ink: '#101113',
  white: '#FFFFFF',
  neutral100: '#F3F3F3',
  neutral200: '#EAEAEA',
  neutral300: '#E6E6E6',
  textMuted: '#62656E',
  textSubtle: '#9B948D',
  textLight: '#D8D9DB',
  navy: '#3B3F63',
  whatsapp: '#25D366',
  positive: '#01A65A',
  danger: '#E84A3F',
  /** Bordure signature sur fond blanc */
  borderNavy20: 'rgba(59, 63, 99, 0.2)',
  borderWhite12: 'rgba(255, 255, 255, 0.12)',
} as const

/** Dégradé marque (boutons / tags — utiliser en background-image linear-gradient côté HTML si besoin) */
export const emailDsGradient = 'linear-gradient(90deg, #E885D0 0%, #FFB84D 100%)'

export const emailDsFonts = {
  /** Stack sûre e-mail (polices web optionnelles via <link> dans preview seulement) */
  display:
    '"Nunito Sans", "Avenir Next", Avenir, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  body: '"Nunito Sans", "Avenir Next", Avenir, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  eyebrow:
    '"Barlow Semi Condensed", "Avenir Next Condensed", Arial, "Helvetica Neue", Helvetica, sans-serif',
} as const

export const emailDsType = {
  h1HeroEmail: { fontSize: 56, fontWeight: 500 as const, lineHeight: 1, letterSpacing: '-0.02em' },
  h2Section: { fontSize: 28, fontWeight: 500 as const, lineHeight: 1.15, letterSpacing: '-0.01em' },
  h3Card: { fontSize: 22, fontWeight: 500 as const, lineHeight: 1.2, letterSpacing: '-0.01em' },
  lead: { fontSize: 15, fontWeight: 400 as const, lineHeight: 1.65 },
  body: { fontSize: 14, fontWeight: 400 as const, lineHeight: 1.6 },
  meta: { fontSize: 12, fontWeight: 500 as const, lineHeight: 1.4, letterSpacing: '0.04em' },
  caption: { fontSize: 11, fontWeight: 400 as const, lineHeight: 1.4 },
  tinyCaps: { fontSize: 10, fontWeight: 500 as const, letterSpacing: '0.08em' },
} as const

export const emailDsLayout = {
  /** Largeur canonique type newsletter (aligné export Figma) */
  contentWidthPx: 600,
  padX: 40,
  padY: 32,
} as const

export const emailDsRadius = {
  pill: 40,
  card: 10,
  chip: 2,
} as const
