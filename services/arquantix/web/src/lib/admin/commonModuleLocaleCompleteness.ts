import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'
import type { CommonModuleEntryStored } from '@/lib/cms/commonModulesStorage'
import { resolveCommonModuleDataForLocale } from '@/lib/cms/commonModulesStorage'
import { validateSectionData } from '@/lib/sections/library'

/**
 * Complétude par locale : validation Zod sur données résolues + présence d’un bloc propre.
 */
export function levelForCommonModuleLocale(
  entry: CommonModuleEntryStored,
  locale: Locale,
): LocaleCompletenessLevel {
  const own = entry.locales[locale]
  const hasOwn =
    own != null && typeof own === 'object' && !Array.isArray(own) && Object.keys(own).length > 0

  const resolved = resolveCommonModuleDataForLocale(entry, locale) as Record<string, unknown>
  const v = validateSectionData(entry.sectionKey, resolved)

  if (!v.valid) {
    return hasOwn ? 'partial' : 'missing'
  }

  const nonTrivial = Object.keys(resolved).some((k) => {
    const val = resolved[k]
    return typeof val === 'string' && val.trim().length > 0
  })

  if (!nonTrivial) return 'missing'

  if (locale === entry.defaultLocale) {
    return 'complete'
  }
  return hasOwn ? 'complete' : 'partial'
}

export function computeCommonModuleLocalesCompleteness(
  entry: CommonModuleEntryStored,
): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    out[loc] = levelForCommonModuleLocale(entry, loc)
  }
  return out
}
