import Link from 'next/link'
import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'

function categorySlugList(raw: unknown): string[] {
  if (!Array.isArray(raw)) return []
  return raw.filter((s): s is string => typeof s === 'string')
}

interface SectionBlogMosaicProps {
  title?: string
  showTitle?: boolean
  limit?: number
  locale: string
}

export async function SectionBlogMosaic({
  title,
  showTitle = true,
  limit = 4,
  locale,
}: SectionBlogMosaicProps) {
  // Fetch highlighted articles (exclude featured)
  const highlightedArticles = await prisma.article.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
      isHighlighted: true,
      isFeatured: false,
    },
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
    take: limit,
  })

  if (highlightedArticles.length === 0) {
    return null
  }

  // Get category labels
  const categoriesRaw = await prisma.articleCategory.findMany({
    where: { isActive: true },
    include: { i18n: true },
  })

  // Get presigned URLs and prepare data
  const articlesWithUrls = await Promise.all(
    highlightedArticles.map(async (article) => {
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
      const catSlugs = categorySlugList(article.categorySlugs)
      const categoryLabel =
        catSlugs.length > 0
          ? resolveLabelWithFallback({
              requestedLocale: locale,
              baseLabel: categoriesRaw.find((c) => c.slug === catSlugs[0])?.label || '',
              i18nRows:
                categoriesRaw.find((c) => c.slug === catSlugs[0])?.i18n.map((i) => ({
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
    return null
  }

  return (
    <div className="mb-16">
      {showTitle && title && (
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {validArticles.map((article, index) => (
          <Link
            key={article.id}
            href={`/blog/${article.slug}`}
            className={`group block bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow ${
              index === 0 ? 'md:col-span-1' : ''
            }`}
          >
            <div className="aspect-video overflow-hidden bg-gray-100">
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
            <div className="p-6">
              {article.categoryLabel && (
                <div className="mb-2">
                  <span className="text-xs text-indigo-600 font-semibold uppercase tracking-wide">
                    {article.categoryLabel}
                  </span>
                </div>
              )}
              <h3 className="text-xl font-semibold text-gray-900 mb-3 group-hover:text-indigo-600 transition-colors line-clamp-2">
                {article.title}
              </h3>
              <p className="text-sm text-gray-600 mb-4 line-clamp-2 leading-relaxed">
                {article.standfirst}
              </p>
              <div className="flex items-center gap-3 text-xs text-gray-500">
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
          </Link>
        ))}
      </div>
    </div>
  )
}









