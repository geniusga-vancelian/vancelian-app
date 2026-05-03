import type { Locale } from '@/config/locales'
import { getLocaleOrDefault, isValidLocale } from '@/config/locales'

/**
 * Chemin public pour la page détail d’une offre exclusive / vault CMS.
 * Règle unique côté front : toujours préfixer par la locale (`/fr/projects/...`).
 */
export function localizedExclusiveOfferDetailPath(locale: string, slug: string): string {
  const loc = getLocaleOrDefault(locale)
  if (slug === 'home') return `/${loc}`
  return `/${loc}/projects/${slug}`
}

/** Hub liste projets sous routing CMS localisé (`/[locale]/projects`). */
export function localizedProjectsHubPath(locale: string): string {
  const loc = getLocaleOrDefault(locale)
  return `/${loc}/projects`
}

/**
 * Déduit la locale depuis le premier segment du chemin (`/fr/...` → `fr`).
 * Sinon retourne `defaultLocale` (ex. `/projects` sans préfixe).
 */
export function getPublicLocaleFromPathname(pathname: string | null): Locale {
  if (!pathname) {
    return getLocaleOrDefault(null)
  }
  const first = pathname.split('/').filter(Boolean)[0]
  if (first && isValidLocale(first)) {
    return first
  }
  return getLocaleOrDefault(null)
}
