/**
 * Couche de documentation des **props normalisées** après
 * `mapDataToComponentProps` — sans importer les composants React.
 *
 * Usage : références TypeScript / JSDoc pour les équipes produit et front.
 * Les types restent volontairement **larges** (champs optionnels, `unknown`
 * là où le renderer accepte encore du legacy).
 */

/** Props FAQ après mapping (`FaqSection`). */
export type NormalizedFaqSectionProps = {
  eyebrow?: string
  title?: string
  description?: string
  subtitle?: string
  items?: Array<{ id: string; question: string; answerMarkdown: string }>
  ui?: { expandAllLabel?: string; collapseAllLabel?: string }
}

/** Famille about / features / feature_grid (`SectionAbout`). */
export type NormalizedAboutFamilyProps = {
  title?: string
  description?: string
  content?: string
  items?: Array<{ title: string; description: string }>
  imageUrl?: string
}

/** Bandeau blog « à la une ». */
export type NormalizedBlogHeroProps = {
  eyebrow?: string
  showEyebrow?: boolean
  showStandfirst?: boolean
  showMeta?: boolean
  locale?: string
}

/** Liste blog paginée. */
export type NormalizedBlogFeedProps = {
  title?: string
  showTitle?: boolean
  pageSize?: number
  loadMoreLabel?: string
  emptyStateTitle?: string
  emptyStateBody?: string
  locale?: string
  category?: string
  page?: number
}
