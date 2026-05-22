/**
 * Sélection de la traduction d’un article avec fallback :
 *   locale demandée → defaultLocale (config site) → première ligne disponible.
 *
 * Les screens Flutter envoient `locale=fr` ; pour les contenus seedés ou
 * créés en `en` uniquement, il faut éviter d’afficher le slug à la place
 * du titre (et de répondre 404 sur le détail).
 */
import { defaultLocale } from '@/config/locales'

export interface ArticleI18nLike {
  locale: string
  title: string
  standfirst: string
  coverTitle?: string | null
  metaTitle?: string | null
  metaDescription?: string | null
}

export function pickArticleI18n<T extends ArticleI18nLike>(
  rows: T[] | null | undefined,
  requestedLocale: string,
  fallbackLocale: string = defaultLocale,
): T | null {
  if (!rows || rows.length === 0) return null
  const exact = rows.find((r) => r.locale === requestedLocale)
  if (exact && exact.title) return exact
  const fallback = rows.find((r) => r.locale === fallbackLocale)
  if (fallback && fallback.title) return fallback
  const any = rows.find((r) => r.title) ?? rows[0]
  return any ?? null
}
