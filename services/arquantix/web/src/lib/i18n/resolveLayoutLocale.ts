import { isValidLocale, type Locale } from '@/config/locales'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'

/**
 * Locale pour le layout racine (menu, footer, `html lang`).
 * Priorité au segment d’URL localisé (header posé par le middleware) — ne peut pas être
 * contredit par le cookie (Phase 2A).
 */
export function resolveLayoutLocale(options: {
  pathLocaleHeader: string | null | undefined
  cookieStore: { get: (name: string) => { value?: string } | undefined }
  fallbackLocale?: Locale
}): Locale {
  const raw = options.pathLocaleHeader?.trim()
  if (raw && isValidLocale(raw)) {
    return raw
  }
  return resolvePublicLocale({
    cookieStore: options.cookieStore,
    searchParams: undefined,
    fallbackLocale: options.fallbackLocale,
  }) as Locale
}
