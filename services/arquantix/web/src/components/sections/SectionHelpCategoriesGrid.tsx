import Link from 'next/link'
import { getHelpCollectionWithCategories, getHelpArticlesInCategory } from '@/lib/help/get-help-data'
import { resolveLabelWithFallback } from '@/lib/i18n/resolveLabel'

interface SectionHelpCategoriesGridProps {
  sectionTitle?: string
  sectionSubtitle?: string
  articlesCountLabel?: string
  emptyTitle?: string
  emptySubtitle?: string
  locale: string
  collectionSlug: string
}

export async function SectionHelpCategoriesGrid({
  sectionTitle,
  sectionSubtitle,
  articlesCountLabel = 'articles',
  emptyTitle,
  emptySubtitle,
  locale,
  collectionSlug,
}: SectionHelpCategoriesGridProps) {
  const collection = await getHelpCollectionWithCategories(collectionSlug, locale)
  if (!collection) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <p className="text-gray-500">Collection introuvable</p>
      </div>
    )
  }

  // Get categories for this collection
  const categories = collection.categories || []

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {(sectionTitle || sectionSubtitle) && (
        <div className="mb-8">
          {sectionTitle && (
            <h2 className="text-2xl font-bold text-gray-900 mb-2">{sectionTitle}</h2>
          )}
          {sectionSubtitle && (
            <p className="text-gray-600">{sectionSubtitle}</p>
          )}
        </div>
      )}

      {categories.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map(async (category) => {
            const articles = await getHelpArticlesInCategory(category.id, locale)
            return (
              <Link
                key={category.id}
                href={`/help/${collectionSlug}/${category.slug}`}
                className="group block p-6 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-lg transition-all"
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                      {category.i18n?.[0]?.title || category.slug}
                    </h3>
                    {category.i18n?.[0]?.description && (
                      <p className="text-gray-600 mb-4 line-clamp-2">
                        {category.i18n[0].description}
                      </p>
                    )}
                    <div className="flex items-center">
                      <span className="text-sm text-gray-500">
                        {articles.length} {articlesCountLabel}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
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
  )
}

