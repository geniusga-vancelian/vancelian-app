/**
 * Largeur max du contenu éditorial alignée sur le DS Figma (cartes témoignages, en-têtes de section,
 * grilles stats, corps Company map, etc.).
 *
 * Valeur unique à réutiliser en `className` (chaîne figée pour le scanner Tailwind).
 */
export const ARQUANTIX_CONTENT_TEXT_MAX_PX = 764

/** `max-w-[764px]` — ne pas construire dynamiquement pour que Tailwind inclue la règle. */
export const arquantixContentTextMaxWidthClass = 'max-w-[764px]' as const

/** Bloc centré, pleine largeur jusqu’au max (ex. row témoignage). */
export const arquantixContentTextBlockClass =
  'mx-auto w-full min-w-0 max-w-[764px]' as const
