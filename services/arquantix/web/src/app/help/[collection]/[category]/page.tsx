import { getHelpCategory, getHelpArticles } from '@/lib/help/get-help-data'
import { SectionHelpSearch } from '@/components/sections/SectionHelpSearch'
import { getLocaleFromCookies } from '@/lib/i18n/locale-server'
import { defaultLocale } from '@/config/locales'
import { cookies } from 'next/headers'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { formatArticleDateShort } from '@/lib/blog/formatDates'

interface PageProps {
  params: {
    collection: string
    category: string
  }
}

export async function generateMetadata({ params }: PageProps) {
  const category = await getHelpCategory(params.collection, params.category)
  if (!category) {
    return {
      title: 'Catégorie non trouvée - Arquantix',
    }
  }
  return {
    title: `${category.title} - Centre d'aide Arquantix`,
    description: category.description || undefined,
  }
}

export default async function HelpCategoryPage({ params }: PageProps) {
  const cookieStore = await cookies()
  const locale = await getLocaleFromCookies(cookieStore) || defaultLocale
  const category = await getHelpCategory(params.collection, params.category)
  const articles = await getHelpArticles(params.collection, params.category)

  if (!category) {
    notFound()
  }

  // Get collection title for breadcrumb
  const { getHelpCollection } = await import('@/lib/help/get-help-data')
  const collectionData = await getHelpCollection(params.collection)

  return (
    <div className="min-h-screen bg-white">
      {/* Hero */}
      <div className="bg-gradient-to-b from-indigo-50 to-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-4">
            <Link href="/help" className="hover:text-gray-700">
              Toutes les collections
            </Link>
            <span className="mx-2">/</span>
            {collectionData && (
              <>
                <Link
                  href={`/help/${params.collection}`}
                  className="hover:text-gray-700"
                >
                  {collectionData.title}
                </Link>
                <span className="mx-2">/</span>
              </>
            )}
            <span className="text-gray-900">{category.title}</span>
          </nav>

          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            {category.title}
          </h1>
          {category.description && (
            <p className="text-lg text-gray-600 mb-8">{category.description}</p>
          )}

          {/* Search */}
          <SectionHelpSearch 
            locale={locale}
            collectionSlug={params.collection}
            categorySlug={params.category}
            placeholder="Rechercher un article…"
            hint="Recherchez par mot-clé, question, sujet…"
          />
        </div>
      </div>

      {/* Articles List */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="space-y-4">
          {articles.map((article) => (
            <Link
              key={article.id}
              href={`/help/${params.collection}/${params.category}/${article.slug}`}
              className="block p-6 bg-white border border-gray-200 rounded-lg hover:border-indigo-300 hover:shadow-md transition-all"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-2 hover:text-indigo-600">
                {article.title}
              </h2>
              {article.standfirst && (
                <p className="text-gray-600 mb-3 line-clamp-2">{article.standfirst}</p>
              )}
              <div className="text-sm text-gray-500">
                Mis à jour le {formatArticleDateShort(article.updatedAt)}
              </div>
            </Link>
          ))}
        </div>

        {articles.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">Aucun article disponible dans cette catégorie.</p>
          </div>
        )}
      </div>
    </div>
  )
}

