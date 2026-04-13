import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'

const COOKIE_NAME = 'arquantix-locale'

/**
 * Get locale from Next.js cookies (server-side)
 */
export async function getLocaleFromCookies(cookieStore: any): Promise<Locale> {
  try {
    const cookieLocale = cookieStore.get(COOKIE_NAME)?.value
    if (cookieLocale && supportedLocales.includes(cookieLocale as Locale)) {
      return cookieLocale as Locale
    }
  } catch (error) {
    // Fallback if cookie reading fails
  }
  return defaultLocale
}


