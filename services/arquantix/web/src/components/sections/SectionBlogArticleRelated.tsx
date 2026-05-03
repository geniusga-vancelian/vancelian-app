import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { getLocaleOrDefault } from '@/config/locales'
import { BlogRecentPostsModule, type DsBlogArticle } from '@/components/design-system/Blog/BlogModules'

export interface SectionBlogArticleRelatedProps {
  title?: string
  ctaLabel?: string
  ctaHref?: string
  limit?: number
  emptyTitle?: string
  locale: string
  currentArticleId: string
}

export async function SectionBlogArticleRelated({
  title,
  ctaLabel,
  ctaHref,
  limit = 4,
  emptyTitle,
  locale,
  currentArticleId,
}: SectionBlogArticleRelatedProps) {
  if (!currentArticleId) {
    return null
  }
  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`
  const effectiveLimit = Math.min(Math.max(limit, 1), 8)

  const articles = await prisma.article.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
      id: { not: currentArticleId },
    },
    include: {
      coverMedia: true,
      i18n: {
        where: { locale: activeLocale },
        take: 1,
      },
      blocks: {
        orderBy: { order: 'asc' },
        take: 20,
      },
    },
    orderBy: { publishedAt: 'desc' },
    take: effectiveLimit,
  })

  if (articles.length === 0) {
    if (emptyTitle?.trim()) {
      return (
        <div className="mx-auto max-w-7xl px-4 py-6 text-center text-[#62656e] sm:px-6 lg:px-8">
          {emptyTitle}
        </div>
      )
    }
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
            if (article.coverMedia.key) {
              coverUrl = await getPresignedUrl(article.coverMedia.key)
            } else {
              coverUrl = article.coverMedia.url || ''
            }
          } catch {
            coverUrl = article.coverMedia.url || ''
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

  const cta = ctaHref?.trim() || blogBasePath
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <BlogRecentPostsModule
        title={title?.trim() || siteCommonCta(locale, 'article_related_title')}
        ctaLabel={ctaLabel?.trim() || siteCommonCta(locale, 'view_all')}
        ctaHref={cta}
        articles={items}
        locale={locale}
        minReadLabel={siteCommonCta(locale, 'blog_min_read')}
        noImageLabel={siteCommonCta(locale, 'no_image')}
        layoutVariant="related2x2"
      />
    </div>
  )
}
