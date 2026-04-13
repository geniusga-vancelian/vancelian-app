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

interface SectionBlogHeroProps {
  eyebrow?: string
  showEyebrow?: boolean
  showStandfirst?: boolean
  showMeta?: boolean
  locale: string
}

export async function SectionBlogHero({ 
  eyebrow, 
  showEyebrow = true, 
  showStandfirst = true, 
  showMeta = true,
  locale 
}: SectionBlogHeroProps) {
  // Fetch featured article
  const featuredArticle = await prisma.article.findFirst({
    where: {
      status: ContentStatus.PUBLISHED,
      isFeatured: true,
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
  })

  // Fallback to latest if no featured
  const articleToUse = featuredArticle || await prisma.article.findFirst({
    where: {
      status: ContentStatus.PUBLISHED,
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
  })

  if (!articleToUse) {
    return null
  }

  const i18n = articleToUse.i18n[0]
  if (!i18n) {
    return null
  }

  // Get cover URL
  let coverUrl: string | null = null
  if (articleToUse.coverMedia) {
    try {
      coverUrl = await getPresignedUrl(articleToUse.coverMedia.key)
    } catch (error) {
      console.error('Error getting presigned URL for cover:', error)
    }
  }

  // Calculate reading time
  const readingTime = calculateReadingTime(articleToUse.blocks)

  // Get category labels
  const categoriesRaw = await prisma.articleCategory.findMany({
    where: { isActive: true },
    include: { i18n: true },
  })

  const catSlugs = categorySlugList(articleToUse.categorySlugs)
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

  return (
    <div className="mb-16">
      <Link
        href={`/blog/${articleToUse.slug}`}
        className="group block bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
      >
        <div className="grid md:grid-cols-2 gap-0 md:items-stretch">
          <div className="aspect-video md:aspect-auto overflow-hidden bg-gray-100 relative">
            {coverUrl ? (
              <img
                src={coverUrl}
                alt={i18n.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400">
                No image
              </div>
            )}
          </div>
          <div className="p-8 md:p-12 flex flex-col justify-center bg-white">
            {showEyebrow && eyebrow && (
              <div className="mb-4">
                <span className="text-sm font-semibold text-indigo-600 uppercase tracking-wide">
                  {eyebrow}
                </span>
              </div>
            )}
            {categoryLabel && (
              <div className="mb-4">
                <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold">
                  {categoryLabel}
                </span>
              </div>
            )}
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 group-hover:text-indigo-600 transition-colors">
              {i18n.title}
            </h2>
            {showStandfirst && i18n.standfirst && (
              <p className="text-lg text-gray-600 mb-6 line-clamp-3 leading-relaxed">
                {i18n.standfirst}
              </p>
            )}
            {showMeta && (
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span className="font-semibold">{articleToUse.authorName}</span>
                {articleToUse.publishedAt && (
                  <time dateTime={articleToUse.publishedAt.toISOString()}>
                    {formatArticleDateShort(articleToUse.publishedAt, locale)}
                  </time>
                )}
                <span>•</span>
                <span>{readingTime} min read</span>
              </div>
            )}
          </div>
        </div>
      </Link>
    </div>
  )
}









