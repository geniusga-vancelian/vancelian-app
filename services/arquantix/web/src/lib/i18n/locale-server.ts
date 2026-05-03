import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'

/** Nom du cookie de préférence de langue (partagé avec `resolvePublicLocale`). */
export const ARQUANTIX_LOCALE_COOKIE = 'arquantix-locale'

/**
 * Get locale from Next.js cookies (server-side)
 */
export async function getLocaleFromCookies(cookieStore: any): Promise<Locale> {
  try {
    const cookieLocale = cookieStore.get(ARQUANTIX_LOCALE_COOKIE)?.value
    if (cookieLocale && supportedLocales.includes(cookieLocale as Locale)) {
      return cookieLocale as Locale
    }
  } catch (error) {
    // Fallback if cookie reading fails
  }
  return defaultLocale
}


