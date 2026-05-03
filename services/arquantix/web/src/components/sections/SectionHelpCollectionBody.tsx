import Link from 'next/link'
import { getHelpPublishedGroupedForCollection } from '@/lib/help/get-help-data'
import { ChevronRight } from 'lucide-react'

interface SectionHelpCollectionBodyProps {
  emptyCategoriesTitle?: string
  emptyCategoriesSubtitle?: string
  emptyArticlesTitle?: string
  emptyArticlesSubtitle?: string
  locale: string
  collectionSlug: string
}

export async function SectionHelpCollectionBody({
  emptyCategoriesTitle = 'Aucun regroupement',
  emptyCategoriesSubtitle = 'Ajoutez des tags catégorie sur les articles de cette collection pour les organiser ici.',
  emptyArticlesTitle = 'Aucun article',
  emptyArticlesSubtitle = 'Aucun article dans ce regroupement.',
  locale,
  collectionSlug,
}: SectionHelpCollectionBodyProps) {
  const groups = await getHelpPublishedGroupedForCollection(collectionSlug, locale)

  if (groups.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center py-12">
          <p className="text-gray-900 text-lg font-semibold mb-2">{emptyCategoriesTitle}</p>
          <p className="text-gray-500">{emptyCategoriesSubtitle}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="space-y-12">
        {groups.map(({ tagSlug, title, articles }) => (
          <div key={tagSlug} id={`tag-${tagSlug}`} className="space-y-4 scroll-mt-24">
            <h2 className="text-2xl font-bold text-gray-900">{title}</h2>

            {articles.length === 0 ? (
              <div className="py-6">
                <p className="text-gray-500 text-sm">{emptyArticlesTitle}</p>
                {emptyArticlesSubtitle && (
                  <p className="text-gray-400 text-xs mt-1">{emptyArticlesSubtitle}</p>
                )}
              </div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="divide-y divide-gray-200">
                  {articles.map((article) => (
                    <Link
                      key={article.id}
                      href={`/help/${collectionSlug}/${article.slug}`}
                      className="block px-6 py-4 hover:bg-gray-50 transition-colors group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-base font-medium text-gray-900 group-hover:text-indigo-600 transition-colors">
                          {article.title}
                        </span>
                        <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors flex-shrink-0 ml-4" />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
