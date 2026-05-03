import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { getLocaleOrDefault } from '@/config/locales'
import { BlogCategoryRowsModule, type DsBlogArticle } from '@/components/design-system/Blog/BlogModules'

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
  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`

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

  const articlesWithUrls = await Promise.all(
    articlesToShow.map(async (article) => {
      const i18n = article.i18n[0]
      if (!i18n) return null

      let coverUrl = ''
      if (article.coverMedia) {
        try {
          coverUrl = await getPresignedUrl(article.coverMedia.key)
        } catch {
          coverUrl = ''
        }
      }

      const readingTime = calculateReadingTime(article.blocks)

      return {
        id: article.id,
        slug: `${blogBasePath}/${article.slug}`,
        title: i18n.title,
        standfirst: i18n.standfirst,
        coverUrl,
        authorName: article.authorName,
        publishedAt: article.publishedAt ? article.publishedAt.toISOString() : null,
        readingTime,
      } satisfies DsBlogArticle
    })
  )

  const validArticles = articlesWithUrls.filter((a): a is DsBlogArticle => a !== null)

  if (validArticles.length === 0) {
    return (
      <div className="mb-10 rounded-lg bg-gray-50 px-4 py-12 text-center">
        {emptyStateTitle ? <p className="text-xl font-semibold text-gray-900">{emptyStateTitle}</p> : null}
        {emptyStateBody ? <p className="mt-2 text-gray-600">{emptyStateBody}</p> : null}
      </div>
    )
  }

  return (
    <>
      <BlogCategoryRowsModule
        title={showTitle ? title || 'Categorie' : ''}
        ctaLabel={loadMoreLabel || 'Call to action'}
        ctaHref={`${blogBasePath}${category ? `?category=${category}` : ''}`}
        articles={validArticles}
        locale={locale}
        minReadLabel={siteCommonCta(locale, 'blog_min_read')}
        noImageLabel={siteCommonCta(locale, 'no_image')}
      />
      {hasMore ? (
        <div className="mt-6 text-center">
          <a
            href={`${blogBasePath}${category ? `?category=${category}&page=${page + 1}` : `?page=${page + 1}`}`}
            className="inline-block rounded-full bg-black px-6 py-3 text-sm text-white transition-opacity hover:opacity-85"
          >
            {siteCommonCta(locale, 'load_more')}
          </a>
        </div>
      ) : null}
    </>
  )
}

