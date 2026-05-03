import { figmaDsColors } from './colors'

/**
 * Hex du canevas page par défaut (pages CMS vides, coque avant modules).
 * Les modules peuvent encore poser `gray100` / bandeaux ; le socle reste blanc.
 */
export const figmaDsPageCanvasHex = figmaDsColors.background.light

/** Fond canevas — équivalent Tailwind de {@link figmaDsPageCanvasHex}. */
export const figmaDsPageCanvasBgClassName = 'bg-white' as const

/**
 * `<body>` racine (`app/layout.tsx`) : hauteur min + canevas DS + lissage.
 */
export const figmaDsBodyRootClassName =
  `min-h-screen ${figmaDsPageCanvasBgClassName} antialiased` as const

/**
 * Enveloppe site claire sous la nav (`SiteChrome`) : canevas + couleur de texte corps.
 */
export const figmaDsSiteShellLightClassName =
  `min-h-screen ${figmaDsPageCanvasBgClassName} text-neutral-900` as const
