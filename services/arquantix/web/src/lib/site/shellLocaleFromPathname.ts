import { getActiveLocaleFromPathname } from '@/lib/i18n/publicLocalizedRouting'
import type { Locale } from '@/config/locales'

/** Locale publique déduite du pathname (stable pour cache menu / footer). */
export function shellLocaleFromPathname(pathname: string): Locale {
  return getActiveLocaleFromPathname(pathname)
}
