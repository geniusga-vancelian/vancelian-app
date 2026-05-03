import {
  getHelpArticle,
  getHelpPublishedGroupedForCollection,
  getHelpArticles,
  getHelpCategory,
  getHelpCollection,
} from '@/lib/help/get-help-data'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { notFound } from 'next/navigation'
import { Metadata } from 'next'
import Link from 'next/link'
import { SectionHelpSearch } from '@/components/sections/SectionHelpSearch'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { HelpArticlePublicPage } from '@/components/help/HelpArticlePublicPage'

interface PageProps {
  params: { collection: string; segment: string }
  searchParams?: Record<string, string | string[] | undefined>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const article = await getHelpArticle(params.collection, params.segment)
  if (article) {
    return {
      title: article.metaTitle || article.title,
      description: article.metaDescription || article.standfirst || undefined,
    }
  }

  const pseudoCategory = await getHelpCategory(params.collection, params.segment)
  if (pseudoCategory) {
    return {
      title: `${pseudoCategory.title} - Centre d'aide Arquantix`,
      description: pseudoCategory.description || undefined,
    }
  }

  return { title: "Centre d'aide Arquantix" }
}

export default async function HelpCollectionSegmentPage({ params, searchParams }: PageProps) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams })

  const collectionData = await getHelpCollection(params.collection)
  if (!collectionData) {
    notFound()
  }

  const article = await getHelpArticle(params.collection, params.segment, locale)
  if (article) {
    return <HelpArticlePublicPage article={article} collectionSlug={params.collection} />
  }

  const grouped = await getHelpPublishedGroupedForCollection(params.collection, locale)
  const fromTag = grouped.find((g) => g.tagSlug === params.segment)
  const pseudoCategory = await getHelpCategory(params.collection, params.segment)
  const articles = await getHelpArticles(params.collection, params.segment, locale)

  const segmentTitle = pseudoCategory?.title ?? fromTag?.title ?? params.segment
  const segmentDescription = pseudoCategory?.description ?? null

  return (
    <div className="min-h-screen bg-white">
      <div className="bg-gradient-to-b from-indigo-50 to-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <nav className="text-sm text-gray-500 mb-4">
            <Link href="/help" className="hover:text-gray-700">
              Toutes les collections
            </Link>
            <span className="mx-2">/</span>
            <Link href={`/help/${params.collection}`} className="hover:text-gray-700">
              {collectionData.title}
            </Link>
            <span className="mx-2">/</span>
            <span className="text-gray-900">{segmentTitle}</span>
          </nav>

          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">{segmentTitle}</h1>
          {segmentDescription && (
            <p className="text-lg text-gray-600 mb-8">{segmentDescription}</p>
          )}

          <SectionHelpSearch
            locale={locale}
            collectionSlug={params.collection}
            categorySlug={params.segment}
            placeholder="Rechercher un article…"
            hint="Recherchez par mot-clé, question, sujet…"
          />
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-4">
          {articles.map((a) => (
            <Link
              key={a.id}
              href={`/help/${params.collection}/${a.slug}`}
              className="block p-6 bg-white border border-gray-200 rounded-lg hover:border-indigo-300 hover:shadow-md transition-all"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-2 hover:text-indigo-600">
                {a.title}
              </h2>
              {a.standfirst && (
                <p className="text-gray-600 mb-3 line-clamp-2">{a.standfirst}</p>
              )}
              <div className="text-sm text-gray-500">
                Mis à jour le {formatArticleDateShort(a.updatedAt)}
              </div>
            </Link>
          ))}
        </div>

        {articles.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">Aucun article disponible pour ce regroupement.</p>
          </div>
        )}
      </div>
    </div>
  )
}
