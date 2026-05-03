import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { getLocaleOrDefault } from '@/config/locales'
import { BlogRecentPostsModule, type DsBlogArticle } from '@/components/design-system/Blog/BlogModules'
import { normalizeBlogMosaicLimit } from '@/lib/blog/normalizeBlogMosaicLimit'

const BLOG_LIST_VALID_SEGMENTS = new Set(['market', 'company', 'analysis'])

function buildBlogListingUrl(
  blogBasePath: string,
  opts: { mosaicPage: number; feedPage: number; category?: string; segment?: string },
): string {
  const params = new URLSearchParams()
  if (opts.category) params.set('category', opts.category)
  if (opts.segment && BLOG_LIST_VALID_SEGMENTS.has(opts.segment)) {
    params.set('segment', opts.segment)
  }
  if (opts.feedPage > 1) params.set('page', String(opts.feedPage))
  if (opts.mosaicPage > 1) params.set('mosaicPage', String(opts.mosaicPage))
  const q = params.toString()
  return `${blogBasePath}${q ? `?${q}` : ''}`
}

interface SectionBlogMosaicProps {
  title?: string
  /** Conservé pour le CMS / mapping ; le bouton « tout voir » n’est plus affiché sur la mosaïque. */
  ctaLabel?: string
  /** Libellés boutons pagination (CMS / traduction). */
  paginationPrevLabel?: string
  paginationNextLabel?: string
  showTitle?: boolean
  limit?: number
  locale: string
  mosaicPage?: number
  blogFeedPage?: number
  category?: string
  blogSegment?: string
}

export async function SectionBlogMosaic({
  title,
  paginationPrevLabel,
  paginationNextLabel,
  showTitle = true,
  limit = 3,
  locale,
  mosaicPage: mosaicPageRaw = 1,
  blogFeedPage = 1,
  category,
  blogSegment,
}: SectionBlogMosaicProps) {
  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`
  const pageSize = normalizeBlogMosaicLimit(limit)

  const where = {
    status: ContentStatus.PUBLISHED,
    isFeatured: false,
  }

  const totalCount = await prisma.article.count({ where })

  if (totalCount === 0) {
    return null
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  let mosaicPage =
    Number.isFinite(mosaicPageRaw) && mosaicPageRaw >= 1 ? Math.floor(mosaicPageRaw) : 1
  mosaicPage = Math.min(mosaicPage, totalPages)

  const articles = await prisma.article.findMany({
    where,
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
    skip: (mosaicPage - 1) * pageSize,
    take: pageSize,
  })

  if (articles.length === 0) {
    return null
  }

  const items = (
    await Promise.all(
      articles.map(async (article) => {
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
      }),
    )
  ).filter((a): a is DsBlogArticle => a !== null)

  if (items.length === 0) {
    return null
  }

  const urlOpts = {
    feedPage: blogFeedPage,
    category,
    segment: blogSegment,
  }

  const mosaicPagination =
    totalPages > 1
      ? {
          currentPage: mosaicPage,
          totalPages,
          prevHref:
            mosaicPage > 1
              ? buildBlogListingUrl(blogBasePath, { ...urlOpts, mosaicPage: mosaicPage - 1 })
              : null,
          nextHref:
            mosaicPage < totalPages
              ? buildBlogListingUrl(blogBasePath, { ...urlOpts, mosaicPage: mosaicPage + 1 })
              : null,
          prevLabel:
            paginationPrevLabel?.trim() || siteCommonCta(locale, 'previous'),
          nextLabel:
            paginationNextLabel?.trim() || siteCommonCta(locale, 'next'),
        }
      : undefined

  return (
    <BlogRecentPostsModule
      title={showTitle ? title || siteCommonCta(locale, 'blog_latest_articles') : ''}
      articles={items}
      locale={locale}
      minReadLabel={siteCommonCta(locale, 'blog_min_read')}
      noImageLabel={siteCommonCta(locale, 'no_image')}
      mosaicPagination={mosaicPagination}
      showHeaderCta={false}
    />
  )
}
