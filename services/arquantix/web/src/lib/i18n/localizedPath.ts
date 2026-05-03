import { isValidLocale, type Locale } from '@/config/locales'
import { LEGACY_UNPREFIXED_TOP_LEVEL } from '@/lib/i18n/legacyUnprefixedPaths'

/**
 * Construit le chemin équivalent pour une nouvelle locale (menu, switcher).
 * Retourne `null` si la route n’est pas du périmètre CMS localisé (blog, projects, etc.) — le caller ne fait que cookie + refresh.
 */
export function getLocalizedPathForLocale(pathname: string, newLocale: Locale): string | null {
  const raw = pathname || '/'
  const p = raw.endsWith('/') && raw.length > 1 ? raw.slice(0, -1) : raw

  const prefixed = p.match(/^\/(fr|en|it)(\/.*)?$/)
  if (prefixed) {
    const rest = prefixed[2] ?? ''
    return `/${newLocale}${rest}` || `/${newLocale}`
  }

  if (p === '/' || p === '') {
    return `/${newLocale}`
  }

  const one = p.match(/^\/([^/.]+)$/)
  if (one) {
    const seg = one[1]
    if (LEGACY_UNPREFIXED_TOP_LEVEL.has(seg)) return null
    if (isValidLocale(seg)) return `/${newLocale}`
    return `/${newLocale}/${seg}`
  }

  return null
}
