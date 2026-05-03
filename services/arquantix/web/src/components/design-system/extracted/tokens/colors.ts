/**
 * Palette extraite du module About Figma (référence documentation).
 */

export const figmaDsColors = {
  primary: {
    black: '#000000',
    white: '#FFFFFF',
  },
  neutral: {
    gray100: '#F3F3F3',
    gray500: '#62656E',
    gray900: '#000000',
  },
  text: {
    primary: '#000000',
    secondary: '#62656E',
    inverse: '#F3F3F3',
  },
  background: {
    /**
     * Canevas page (body, coque site) — blanc 100 %, init pages CMS.
     * Ne pas confondre avec `neutral.gray100` (bandeaux / encarts).
     */
    light: '#FFFFFF',
    /** Alias sémantique = `light` (documentation / consommation TS). */
    pageCanvas: '#FFFFFF',
    medium: '#F3F3F3',
    dark: '#000000',
  },
  border: {
    light: '#F3F3F3',
    medium: '#62656E',
  },
} as const

export type FigmaDsColorToken = typeof figmaDsColors
