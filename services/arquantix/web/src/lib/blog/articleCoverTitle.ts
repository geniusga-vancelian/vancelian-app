/**
 * Légende sous la couverture : priorité à la variante i18n, repli sur `articles.cover_title`
 * (champ historique / synchro locale par défaut).
 */
export function effectiveArticleCoverTitle(
  i18nCoverTitle: string | null | undefined,
  articleCoverTitle: string | null | undefined,
): string | undefined {
  const fromI18n = typeof i18nCoverTitle === 'string' ? i18nCoverTitle.trim() : ''
  if (fromI18n.length > 0) {
    return i18nCoverTitle as string
  }
  const fromArticle = typeof articleCoverTitle === 'string' ? articleCoverTitle.trim() : ''
  if (fromArticle.length > 0) {
    return articleCoverTitle as string
  }
  return undefined
}
