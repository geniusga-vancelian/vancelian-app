/**
 * Palette extraite — remappée sur le Design System Vancelian.
 *
 * Source : `src/styles/vancelian-tokens.css` (variables `--v-*`).
 * Ces constantes sont la projection TypeScript des tokens DS pour les
 * consommateurs qui ont besoin de hex statiques (mock data, SVGR, etc.).
 *
 * Pour le CSS, préférer `var(--v-bg)`, `var(--v-fg)`, etc.
 */

export const figmaDsColors = {
  primary: {
    /** Anthracite Vancelian — jamais noir pur. */
    black: '#1A1815',
    white: '#FFFFFF',
  },
  neutral: {
    /** Papier off-white DS — substitue l'ancien `#F3F3F3`. */
    gray100: '#F2F1ED',
    /** Texte secondaire muted — anthracite atténué. */
    gray500: '#6E665C',
    /** Anthracite plein, foreground principal. */
    gray900: '#1A1815',
  },
  text: {
    primary: '#1A1815',
    secondary: '#6E665C',
    inverse: '#EDECEC',
  },
  background: {
    /**
     * Canevas page (body, coque site) — papier off-white Vancelian.
     * Substitue l'ancien blanc pur. Conforme DS : « jamais blanc 100 % ».
     */
    light: '#F7F7F4',
    /** Alias sémantique = `light` (documentation / consommation TS). */
    pageCanvas: '#F7F7F4',
    /** Carte niveau 1 — l'ancien `#F3F3F3` glisse vers `#F2F1ED`. */
    medium: '#F2F1ED',
    /** Fond dark (footer, final-cta) — `--v-dark-bg`. */
    dark: '#141208',
  },
  border: {
    light: '#E2DED4',
    medium: '#C9C3B5',
  },
} as const

export type FigmaDsColorToken = typeof figmaDsColors
