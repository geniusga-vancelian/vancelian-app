import Link from 'next/link'
import { getHelpCollections, type HelpCollectionWithCount } from '@/lib/help/get-help-data'

interface SectionHelpCollectionsGridProps {
  sectionTitle?: string
  sectionSubtitle?: string
  cardCtaLabel?: string
  articlesCountLabel?: string
  emptyTitle?: string
  emptySubtitle?: string
  locale: string
}

export async function SectionHelpCollectionsGrid({
  sectionTitle,
  sectionSubtitle,
  cardCtaLabel = 'Voir',
  articlesCountLabel = 'articles',
  emptyTitle,
  emptySubtitle,
  locale,
}: SectionHelpCollectionsGridProps) {
  const collections: HelpCollectionWithCount[] = await getHelpCollections(locale)

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

      {collections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {collections.map((collection) => (
            <Link
              key={collection.id}
              href={`/help/${collection.slug}`}
              className="group block p-6 bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-lg transition-all"
            >
              <div className="flex items-start gap-4">
                <div
                  className="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center overflow-hidden bg-indigo-100"
                  style={
                    collection.colorHex
                      ? { backgroundColor: `${collection.colorHex}22` }
                      : undefined
                  }
                >
                  {collection.coverImageUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={collection.coverImageUrl}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <svg
                      className="w-6 h-6 text-indigo-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                    {collection.title}
                  </h3>
                  {collection.subtitle && (
                    <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                      {collection.subtitle}
                    </p>
                  )}
                  {collection.description && (
                    <p className="text-gray-600 mb-4 line-clamp-2">
                      {collection.description}
                    </p>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500">
                      {collection.articleCount} {articlesCountLabel}
                    </span>
                    <span className="text-sm font-medium text-indigo-600 group-hover:text-indigo-700">
                      {cardCtaLabel} →
                    </span>
                  </div>
                </div>
              </div>
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
  )
}

