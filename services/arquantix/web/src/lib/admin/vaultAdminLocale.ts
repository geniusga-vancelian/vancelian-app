/**
 * Champs page (titre / description) affichés dans l’admin Vault pour une locale donnée.
 * Aligné sur l’usage CMS : `PageI18n` par locale, repli sur `Page` pour la locale par défaut.
 */
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'

export type PageI18nRow = { locale: string; title: string | null; description: string | null }

export function getVaultPageTextFieldsForLocale(
  page: { title: string | null; description: string | null },
  pageI18n: PageI18nRow[],
  locale: Locale,
): { title: string; description: string } {
  const row = pageI18n.find((r) => r.locale === locale)
  const title =
    trimNonEmpty(row?.title) ??
    (locale === defaultLocale ? trimNonEmpty(page.title) : null) ??
    ''
  const description =
    trimNonEmpty(row?.description) ??
    (locale === defaultLocale ? trimNonEmpty(page.description) : null) ??
    ''
  return { title, description }
}

function trimNonEmpty(s: string | null | undefined): string | null {
  const t = typeof s === 'string' ? s.trim() : ''
  return t.length > 0 ? t : null
}

export function parseAdminVaultLocale(raw: string | null | undefined): Locale {
  if (raw && isValidLocale(raw)) return raw
  return defaultLocale
}
