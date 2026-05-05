import { cache } from 'react'
import { prisma } from '@/lib/prisma'
import {
  defaultLocale as configDefaultLocale,
  isValidLocale,
  supportedLocales as configSupportedLocales,
  type Locale,
} from '@/config/locales'

export type SiteI18nSettings = {
  defaultLocale: Locale
  /** Locales réellement proposées (sous-ensemble des locales techniques). */
  supportedLocales: Locale[]
  multilingualEnabled: boolean
}

function parseSupportedLocalesJson(raw: string | null | undefined): Locale[] {
  if (!raw?.trim()) return [...configSupportedLocales]
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return [...configSupportedLocales]
    return parsed.filter((x): x is Locale => typeof x === 'string' && isValidLocale(x))
  } catch {
    return [...configSupportedLocales]
  }
}

/**
 * Lecture DB sans cache React — route handlers, middleware (via fetch interne).
 */
export async function getSiteI18nSettingsUncached(): Promise<SiteI18nSettings> {
  try {
    const row = await prisma.appSettings.findUnique({ where: { id: 'default' } })
    if (!row) {
      return {
        defaultLocale: configDefaultLocale,
        supportedLocales: [...configSupportedLocales],
        multilingualEnabled: true,
      }
    }

    const fromDb = parseSupportedLocalesJson(row.supportedLocales)
    const supportedLocales = fromDb.length > 0 ? fromDb : [...configSupportedLocales]

    const dl =
      row.defaultLocale && isValidLocale(row.defaultLocale) ? row.defaultLocale : configDefaultLocale

    const filteredSupported = supportedLocales.includes(dl)
      ? supportedLocales
      : [dl, ...supportedLocales.filter((l) => l !== dl)]

    return {
      defaultLocale: dl,
      supportedLocales: filteredSupported,
      multilingualEnabled: row.multilingualEnabled !== false,
    }
  } catch {
    return {
      defaultLocale: configDefaultLocale,
      supportedLocales: [...configSupportedLocales],
      multilingualEnabled: true,
    }
  }
}

/**
 * Paramètres i18n site (table `app_settings`), mis en cache par requête RSC.
 */
export const getSiteI18nSettingsCached = cache(getSiteI18nSettingsUncached)

/** Menu public : afficher le switcher seulement si multilingue activé et ≥ 2 locales. */
export function shouldShowPublicLanguageSwitcher(settings: SiteI18nSettings): boolean {
  return settings.multilingualEnabled && settings.supportedLocales.length > 1
}
