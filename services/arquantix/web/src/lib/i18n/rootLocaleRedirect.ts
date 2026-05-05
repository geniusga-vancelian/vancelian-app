import type { NextRequest } from 'next/server'
import { defaultLocale, isValidLocale, supportedLocales, type Locale } from '@/config/locales'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'
import type { SitePublicI18nPolicy } from '@/lib/i18n/siteI18nPolicyCookie'

/**
 * Sources communes middleware + page racine pour `/` → `/{locale}`.
 */
export function pickLocaleForRootFromSources(input: {
  localeQuery: string | null | undefined
  cookieLocale: string | null | undefined
  acceptLanguage: string | null | undefined
  /** Dernier recours — `AppSettings.default_locale`, pas le défaut compile-time seul. */
  fallbackLocale?: Locale
}): Locale {
  if (input.localeQuery && isValidLocale(input.localeQuery)) {
    return input.localeQuery
  }
  if (input.cookieLocale && isValidLocale(input.cookieLocale)) {
    return input.cookieLocale
  }
  /** Langue par défaut site (admin) avant deviner via Accept-Language — produit EN-first. */
  if (input.fallbackLocale && isValidLocale(input.fallbackLocale)) {
    return input.fallbackLocale
  }
  const fromAl = pickLocaleFromAcceptLanguage(input.acceptLanguage ?? null)
  if (fromAl) {
    return fromAl
  }
  return defaultLocale
}

/**
 * `/` → locale cible. Si le site est monolingue (`policy`), on ignore cookie navigateur
 * et Accept-Language pour forcer la langue par défaut admin.
 */
export function pickLocaleForRootRedirect(
  request: NextRequest,
  policy: SitePublicI18nPolicy,
): Locale {
  if (!policy.multilingual) {
    return policy.defaultLocale
  }

  return pickLocaleForRootFromSources({
    localeQuery: request.nextUrl.searchParams.get('locale'),
    cookieLocale: request.cookies.get(ARQUANTIX_LOCALE_COOKIE)?.value,
    acceptLanguage: request.headers.get('accept-language'),
    fallbackLocale: policy.defaultLocale,
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

/** Remplace le premier segment de locale dans le chemin (ex. `/fr/a` → `/en/a`). */
export function replaceLeadingLocaleInPathname(pathname: string, newLocale: Locale): string {
  const m = pathname.match(/^\/(fr|en|it)(\/.*)?$/)
  if (!m?.[1] || !isValidLocale(m[1])) {
    return pathname
  }
  const rest = m[2] ?? ''
  return `/${newLocale}${rest}`
}
