export const defaultLocale = 'fr'
export const supportedLocales = ['fr', 'en', 'it'] as const

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

