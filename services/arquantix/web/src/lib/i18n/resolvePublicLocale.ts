import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'

function pickQueryLocale(
  searchParams?: Record<string, string | string[] | undefined> | null,
): string | undefined {
  if (!searchParams) return undefined
  const v = searchParams.locale
  if (Array.isArray(v)) return v[0]
  return v
}

/**
 * Locale pour pages publiques et preview CMS.
 * Priorité par défaut : segment d’URL (`urlLocale`) → cookie `arquantix-locale` → `searchParams.locale` → `defaultLocale`.
 *
 * Avec `preferQueryLocaleOverCookie`, `?locale=` passe **avant** le cookie (iframe d’aperçu admin
 * où l’URL est la source de vérité, sinon le cookie navigateur fige la langue).
 */
export function resolvePublicLocale(options: {
  cookieStore: { get: (name: string) => { value?: string } | undefined }
  searchParams?: Record<string, string | string[] | undefined> | null
  /** Ex. `/fr/projects/slug` → `fr` — doit primer sur cookie pour cohérence barre d’adresse. */
  urlLocale?: string | null
  preferQueryLocaleOverCookie?: boolean
}): Locale {
  const q = pickQueryLocale(options.searchParams ?? undefined)

  if (options.urlLocale && isValidLocale(options.urlLocale)) {
    return options.urlLocale
  }

  if (options.preferQueryLocaleOverCookie === true && q && isValidLocale(q)) {
    return q
  }

  const rawCookie = options.cookieStore.get(ARQUANTIX_LOCALE_COOKIE)?.value
  if (rawCookie && isValidLocale(rawCookie)) {
    return rawCookie
  }

  if (q && isValidLocale(q)) {
    return q
  }

  return defaultLocale
}
