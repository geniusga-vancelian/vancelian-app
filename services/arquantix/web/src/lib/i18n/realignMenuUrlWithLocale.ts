import type { Locale } from '@/config/locales'
import { localizePublicInternalHref } from '@/lib/i18n/publicLocalizedRouting'

/**
 * @deprecated Préférer `localizePublicInternalHref` depuis `@/lib/i18n/publicLocalizedRouting`.
 * Conservé pour imports historiques (navbar, tests).
 */
export function realignPrimaryMenuUrlForActiveLocale(
  path: string,
  activeLocale: Locale,
): string {
  return localizePublicInternalHref(path, activeLocale)
}
