/**
 * Helper to resolve localized labels with fallback chain
 * Fallback: requested locale -> default locale -> base label
 */

export const SUPPORTED_LOCALES = ['fr', 'en', 'it'] as const
export const DEFAULT_LOCALE = 'fr' as const

export type SupportedLocale = typeof SUPPORTED_LOCALES[number]

export interface I18nRow {
  locale: string
  label: string
}

export interface ResolveLabelOptions {
  requestedLocale: string
  defaultLocale?: string
  baseLabel: string
  i18nRows: I18nRow[]
}

/**
 * Resolve label with fallback chain:
 * 1. Try requested locale
 * 2. Try default locale (fr)
 * 3. Fallback to base label
 */
export function resolveLabelWithFallback({
  requestedLocale,
  defaultLocale = DEFAULT_LOCALE,
  baseLabel,
  i18nRows,
}: ResolveLabelOptions): string {
  // Try requested locale first
  const requestedRow = i18nRows.find((row) => row.locale === requestedLocale)
  if (requestedRow?.label) {
    return requestedRow.label
  }

  // Try default locale
  const defaultRow = i18nRows.find((row) => row.locale === defaultLocale)
  if (defaultRow?.label) {
    return defaultRow.label
  }

  // Fallback to base label
  return baseLabel
}


