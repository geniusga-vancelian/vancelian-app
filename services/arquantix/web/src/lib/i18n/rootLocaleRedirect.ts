import type { NextRequest } from 'next/server'
import { defaultLocale, isValidLocale, supportedLocales, type Locale } from '@/config/locales'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'

/**
 * Sources communes middleware + page racine pour `/` → `/{locale}`.
 */
export function pickLocaleForRootFromSources(input: {
  localeQuery: string | null | undefined
  cookieLocale: string | null | undefined
  acceptLanguage: string | null | undefined
}): Locale {
  if (input.localeQuery && isValidLocale(input.localeQuery)) {
    return input.localeQuery
  }
  if (input.cookieLocale && isValidLocale(input.cookieLocale)) {
    return input.cookieLocale
  }
  const fromAl = pickLocaleFromAcceptLanguage(input.acceptLanguage ?? null)
  if (fromAl) {
    return fromAl
  }
  return defaultLocale
}

/**
 * Locale cible pour une redirection `/` → `/{locale}` (middleware Phase 2A).
 * Ordre : `?locale=` valide → cookie → Accept-Language → défaut.
 */
export function pickLocaleForRootRedirect(request: NextRequest): Locale {
  return pickLocaleForRootFromSources({
    localeQuery: request.nextUrl.searchParams.get('locale'),
    cookieLocale: request.cookies.get(ARQUANTIX_LOCALE_COOKIE)?.value,
    acceptLanguage: request.headers.get('accept-language'),
  })
}

function pickLocaleFromAcceptLanguage(header: string | null): Locale | null {
  if (!header?.trim()) return null
  const lowered = header.toLowerCase()
  for (const loc of supportedLocales) {
    if (lowered.includes(loc)) {
      return loc
    }
  }
  return null
}
