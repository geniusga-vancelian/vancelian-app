import { figmaDsColors } from './colors'

/**
 * Hex du canevas page par défaut.
 *
 * Aligné sur le DS Vancelian (papier off-white `--v-bg = #F7F7F4`).
 * L'ancien blanc pur n'est plus utilisé : il a été remplacé par cette
 * teinte « papier » non blanche, qui sert de socle à toute l'app publique.
 */
export const figmaDsPageCanvasHex: string = figmaDsColors.background.pageCanvas

/** Fond canevas — équivalent Tailwind de {@link figmaDsPageCanvasHex}. */
export const figmaDsPageCanvasBgClassName = 'bg-v-bg' as const

/**
 * `<body>` racine (`app/layout.tsx`) : hauteur min + canevas DS + lissage.
 */
export const figmaDsBodyRootClassName =
  `min-h-screen ${figmaDsPageCanvasBgClassName} text-v-fg antialiased` as const

/**
 * Enveloppe site claire sous la nav (`SiteChrome`) : canevas + couleur de texte corps.
 */
export const figmaDsSiteShellLightClassName =
  `min-h-screen ${figmaDsPageCanvasBgClassName} text-v-fg` as const
