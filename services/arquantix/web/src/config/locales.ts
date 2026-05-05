/** Locale canonique / fallback compile-time (alignée avec `AppSettings.default_locale` en prod). */
export const defaultLocale = 'en'
export const supportedLocales = ['en', 'fr', 'it'] as const

export type Locale = (typeof supportedLocales)[number]

export function isValidLocale(locale: string): locale is Locale {
  return supportedLocales.includes(locale as Locale)
}

export function getLocaleOrDefault(locale: string | null | undefined): Locale {
  if (locale && isValidLocale(locale)) {
    return locale
  }
  return defaultLocale
}
