import Link from 'next/link'
import { getHelpArticles } from '@/lib/help/get-help-data'
import { formatArticleDateShort } from '@/lib/blog/formatDates'

interface SectionHelpSearchResultsProps {
  resultsTitle?: string
  resultsCountLabel?: string
  emptyTitle?: string
  emptySubtitle?: string
  locale: string
  collectionSlug?: string
  categorySlug?: string
  searchQuery?: string
}

export async function SectionHelpSearchResults({
  resultsTitle = 'Résultats',
  resultsCountLabel = 'résultats',
  emptyTitle = 'Aucun article trouvé',
  emptySubtitle = 'Essayez une autre recherche.',
  locale,
  collectionSlug,
  categorySlug,
  searchQuery,
}: SectionHelpSearchResultsProps) {
  let articles: Array<{
    id: string
    slug: string
    title: string
    standfirst?: string | null
    updatedAt: Date
  }> = []

  if (collectionSlug && categorySlug) {
    // Get articles from category
    articles = await getHelpArticles(collectionSlug, categorySlug, locale)
  }

  // Filter by search query if provided
  if (searchQuery) {
    const queryLower = searchQuery.toLowerCase()
    articles = articles.filter(
      (article) =>
        article.title.toLowerCase().includes(queryLower) ||
        article.standfirst?.toLowerCase().includes(queryLower)
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        {searchQuery && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {resultsTitle}
            </h2>
            <p className="text-sm text-gray-500">
              {articles.length} {resultsCountLabel} pour "{searchQuery}"
            </p>
          </div>
        )}

        {articles.length > 0 ? (
          <div className="space-y-4">
            {articles.map((article) => (
              <Link
                key={article.id}
                href={`/help/${collectionSlug}/${article.slug}`}
                className="block p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:shadow-md transition-all"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2 hover:text-indigo-600">
                  {article.title}
                </h3>
                {article.standfirst && (
                  <p className="text-gray-600 mb-2 line-clamp-2">{article.standfirst}</p>
                )}
                <p className="text-xs text-gray-500">
                  Mis à jour {formatArticleDateShort(article.updatedAt, locale)}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            {emptyTitle && (
              <p className="text-lg font-semibold text-gray-900 mb-2">{emptyTitle}</p>
            )}
            {emptySubtitle && (
              <p className="text-gray-500">{emptySubtitle}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}









