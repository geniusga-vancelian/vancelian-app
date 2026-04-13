import Link from 'next/link'
import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'

interface SectionBlogFeedProps {
  title?: string
  showTitle?: boolean
  pageSize?: number
  loadMoreLabel?: string
  emptyStateTitle?: string
  emptyStateBody?: string
  locale: string
  category?: string
  page?: number
}

export async function SectionBlogFeed({
  title,
  showTitle = true,
  pageSize = 10,
  loadMoreLabel = 'Load more',
  emptyStateTitle,
  emptyStateBody,
  locale,
  category,
  page = 1,
}: SectionBlogFeedProps) {
  // Build where clause
  const whereClause: any = {
    status: ContentStatus.PUBLISHED,
    isFeatured: false,
    isHighlighted: false,
  }

  if (category) {
    whereClause.categorySlugs = {
      path: ['$'],
      array_contains: [category],
    }
  }

  // Fetch articles
  const articles = await prisma.article.findMany({
    where: whereClause,
    include: {
      coverMedia: true,
      i18n: {
        where: { locale },
        take: 1,
      },
      blocks: {
        orderBy: { order: 'asc' },
        take: 20,
      },
    },
    orderBy: { publishedAt: 'desc' },
    take: pageSize + 1, // Fetch one extra to check if there's more
    skip: (page - 1) * pageSize,
  })

  const hasMore = articles.length > pageSize
  const articlesToShow = articles.slice(0, pageSize)

  // Get category labels
  const categoriesRaw = await prisma.articleCategory.findMany({
    where: { isActive: true },
    include: { i18n: true },
  })

  // Prepare articles with URLs
  const articlesWithUrls = await Promise.all(
    articlesToShow.map(async (article) => {
      const i18n = article.i18n[0]
      if (!i18n) return null

      let coverUrl: string | null = null
      if (article.coverMedia) {
        try {
          coverUrl = await getPresignedUrl(article.coverMedia.key)
        } catch (error) {
          console.error('Error getting presigned URL:', error)
        }
      }

      const readingTime = calculateReadingTime(article.blocks)
      const categorySlugsArray = Array.isArray(article.categorySlugs) ? article.categorySlugs : []
      const categoryLabel = categorySlugsArray.length > 0
        ? resolveLabelWithFallback({
            requestedLocale: locale,
            baseLabel: categoriesRaw.find(c => c.slug === categorySlugsArray[0])?.label || '',
            i18nRows: categoriesRaw.find(c => c.slug === categorySlugsArray[0])?.i18n.map(i => ({
              locale: i.locale,
              label: i.label,
            })) || [],
          })
        : null

      return {
        id: article.id,
        slug: article.slug,
        title: i18n.title,
        standfirst: i18n.standfirst,
        coverUrl,
        authorName: article.authorName,
        publishedAt: article.publishedAt,
        readingTime,
        categoryLabel,
      }
    })
  )

  const validArticles = articlesWithUrls.filter((a): a is NonNullable<typeof a> => a !== null)

  if (validArticles.length === 0) {
    return (
      <div className="mb-16">
        {showTitle && title && (
          <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
        )}
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          {emptyStateTitle && (
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{emptyStateTitle}</h3>
          )}
          {emptyStateBody && (
            <p className="text-gray-600">{emptyStateBody}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="mb-16">
      {showTitle && title && (
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
      )}
      <div className="space-y-8">
        {validArticles.map((article) => (
          <Link
            key={article.id}
            href={`/blog/${article.slug}`}
            className="group block bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow"
          >
            <div className="grid md:grid-cols-3 gap-6 p-6">
              <div className="md:col-span-1 aspect-video overflow-hidden bg-gray-100 rounded-lg">
                {article.coverUrl ? (
                  <img
                    src={article.coverUrl}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    No image
                  </div>
                )}
              </div>
              <div className="md:col-span-2 flex flex-col justify-center">
                {article.categoryLabel && (
                  <div className="mb-2">
                    <span className="text-xs text-indigo-600 font-semibold uppercase tracking-wide">
                      {article.categoryLabel}
                    </span>
                  </div>
                )}
                <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                  {article.title}
                </h3>
                <p className="text-gray-600 mb-4 line-clamp-2 leading-relaxed">
                  {article.standfirst}
                </p>
                <div className="flex items-center gap-3 text-sm text-gray-500">
                  <span className="font-medium">{article.authorName}</span>
                  {article.publishedAt && (
                    <>
                      <time dateTime={article.publishedAt.toISOString()}>
                        {formatArticleDateShort(article.publishedAt, locale)}
                      </time>
                      <span>•</span>
                    </>
                  )}
                  <span>{article.readingTime} min read</span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
      {hasMore && (
        <div className="mt-8 text-center">
          <Link
            href={`/blog${category ? `?category=${category}&page=${page + 1}` : `?page=${page + 1}`}`}
            className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
          >
            {loadMoreLabel}
          </Link>
        </div>
      )}
    </div>
  )
}

