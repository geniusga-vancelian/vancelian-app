/**
 * Source unique des tokens utilisés par :
 * - les composants MJML (au build, via lecture JSON dans `mjmlRender`),
 * - le DS React inline `src/email-ds/` (re-export typé).
 *
 * Toute mise à jour de `colors.json`, `typography.json` ou `layout.json`
 * se propage automatiquement aux deux pipelines.
 */
import colorsJson from './colors.json'
import typographyJson from './typography.json'
import layoutJson from './layout.json'

export const emailTokens = {
  colors: colorsJson as Readonly<Record<string, string>>,
  fonts: typographyJson.fonts as Readonly<Record<'display' | 'body' | 'eyebrow' | 'mono', string>>,
  type: typographyJson.scale as Readonly<
    Record<
      string,
      { size: number; weight: number; lineHeight: string; letterSpacing?: string }
    >
  >,
  layout: layoutJson as Readonly<{
    contentWidthPx: number
    padX: number
    padY: number
    radius: { pill: number; card: number; chip: number }
  }>,
} as const

export type EmailTokens = typeof emailTokens
