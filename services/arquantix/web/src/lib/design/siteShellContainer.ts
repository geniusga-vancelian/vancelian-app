/**
 * Grille horizontale topnav — alignée sur `Navigation.tsx`.
 * Pour le contenu des pages / modules CMS, utiliser le composant `<Container>` (classe `.v-container`).
 *
 * max-width 1280px · padding 48px (lg+) · 24px (md) · 16px (sm) · 48px (< sm, spec topnav).
 */
export const siteShellMaxWidthClassName = 'max-w-[1280px]' as const

export const siteShellHorizontalPaddingClassName =
  'px-12 sm:px-4 md:px-6 lg:px-12' as const

/** Conteneur centré (navbar, modules CMS, footer). */
export const siteShellContainerClassName =
  `mx-auto w-full ${siteShellMaxWidthClassName} ${siteShellHorizontalPaddingClassName}` as const
