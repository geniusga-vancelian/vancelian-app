/**
 * Couche unique : chemins publics internes localisés (`/{locale}/…`).
 * Côté client, la locale active = premier segment `fr|en|it` du pathname quand présent
 * (`getActiveLocaleFromPathname`), sinon locale par défaut du site.
 */

import type { Locale } from '@/config/locales'
import { getLocaleOrDefault } from '@/config/locales'
import { LEGACY_UNPREFIXED_TOP_LEVEL } from '@/lib/i18n/legacyUnprefixedPaths'
import {
  getPublicLocaleFromPathname,
  localizedExclusiveOfferDetailPath,
  localizedProjectsHubPath,
} from '@/lib/i18n/localizedExclusiveOfferPath'

export { getPublicLocaleFromPathname as getActiveLocaleFromPathname }

export function buildLocalizedProjectHubPath(locale: string): string {
  return localizedProjectsHubPath(locale)
}

export function buildLocalizedProjectDetailPath(locale: string, slug: string): string {
  return localizedExclusiveOfferDetailPath(locale, slug)
}

export function buildLocalizedHomePath(locale: string): string {
  return `/${getLocaleOrDefault(locale)}`
}

/** Page CMS sous `/{locale}/{slug}` (`home` → racine localisée). */
export function buildLocalizedCmsPagePath(locale: string, pageSlug: string): string {
  const loc = getLocaleOrDefault(locale)
  if (pageSlug === 'home') return `/${loc}`
  return `/${loc}/${pageSlug}`
}

/** Liens à ne pas réécrire (ancres, absolus, messageries). */
export function shouldSkipLocalizePublicHref(href: string): boolean {
  const h = href.trim()
  if (!h || h.startsWith('#')) return true
  if (/^https?:\/\//i.test(h)) return true
  if (/^mailto:/i.test(h)) return true
  if (/^tel:/i.test(h)) return true
  if (h.startsWith('//')) return true
  if (/wa\.me|api\.whatsapp|whatsapp\.com/i.test(h)) return true
  return false
}

/** Ouvrir dans un nouvel onglet (URLs absolues / messageries), pas les chemins relatifs `/…`. */
export function isPublicHrefExternalNavigation(href: string): boolean {
  const h = href.trim()
  if (!h || h.startsWith('#')) return false
  if (/^https?:\/\//i.test(h)) return true
  if (/^mailto:/i.test(h)) return true
  if (/^tel:/i.test(h)) return true
  if (h.startsWith('//')) return true
  if (/wa\.me|api\.whatsapp|whatsapp\.com/i.test(h)) return true
  return false
}

/**
 * Réaligne tout chemin interne « stocké » (menu, CMS, `detailUrl`) sur la locale active.
 * Laisse inchangés : legacy top-level (`/blog/...`, `/help/...`), URLs externes, ancres.
 */
export function localizePublicInternalHref(path: string, activeLocale: Locale): string {
  const raw = (path || '').trim()
  if (!raw || shouldSkipLocalizePublicHref(raw)) return raw
  if (!raw.startsWith('/')) return raw

  const loc = getLocaleOrDefault(activeLocale)

  if (/^\/(fr|en|it)(\/|$)/.test(raw)) {
    return raw.replace(/^\/(fr|en|it)(?=\/|$)/, `/${loc}`)
  }

  if (raw === '/projects') {
    return localizedProjectsHubPath(loc)
  }

  if (raw.startsWith('/projects/')) {
    const slug = raw.slice('/projects/'.length).replace(/\/$/, '')
    if (slug) {
      return localizedExclusiveOfferDetailPath(loc, slug)
    }
    return localizedProjectsHubPath(loc)
  }

  if (raw === '/') {
    return `/${loc}`
  }

  const segments = raw.split('/').filter(Boolean)
  const first = segments[0]!

  if (segments.length === 1) {
    if (LEGACY_UNPREFIXED_TOP_LEVEL.has(first)) {
      return `/${first}`
    }
    return `/${loc}/${first}`
  }

  if (LEGACY_UNPREFIXED_TOP_LEVEL.has(first)) {
    return '/' + segments.join('/')
  }

  return `/${loc}/${segments.join('/')}`
}
