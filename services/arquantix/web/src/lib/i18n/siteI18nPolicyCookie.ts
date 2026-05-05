import { isValidLocale, type Locale } from '@/config/locales'

/** Cookie côté navigateur : politique i18n publique (sync admin / DB), lu par le middleware. */
export const ARQUANTIX_SITE_I18N_COOKIE = 'arquantix-site-i18n'

export type SitePublicI18nPolicy = {
  multilingual: boolean
  defaultLocale: Locale
}

/** Format : `1` ou `0` puis `.` puis code locale (ex. `0.en`). */
export function encodeSiteI18nCookie(policy: SitePublicI18nPolicy): string {
  const m = policy.multilingual ? '1' : '0'
  return `${m}.${policy.defaultLocale}`
}

export function parseSiteI18nCookie(raw: string | null | undefined): SitePublicI18nPolicy | null {
  if (!raw?.trim()) return null
  const [a, b] = raw.trim().split('.')
  if ((a !== '0' && a !== '1') || !b || !isValidLocale(b)) return null
  return { multilingual: a === '1', defaultLocale: b }
}

/** Options communes pour `cookies.set`. */
export function buildSiteI18nCookieSetOptions(): {
  path: string
  maxAge: number
  sameSite: 'lax'
  secure: boolean
} {
  return {
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  }
}
