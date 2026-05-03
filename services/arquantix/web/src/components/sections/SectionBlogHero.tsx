import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { getLocaleOrDefault } from '@/config/locales'
import { BlogFeaturedModule, type DsBlogArticle } from '@/components/design-system/Blog/BlogModules'

interface SectionBlogHeroProps {
  eyebrow?: string
  showEyebrow?: boolean
  showStandfirst?: boolean
  showMeta?: boolean
  locale: string
  /** Premier bloc blog : fond gray100 jusqu’en haut, sous le menu primaire. */
  bleedUnderPrimaryNav?: boolean
}

export async function SectionBlogHero({ 
  eyebrow, 
  showEyebrow = true, 
  showStandfirst = true, 
  showMeta = true,
  locale,
  bleedUnderPrimaryNav = false,
}: SectionBlogHeroProps) {
  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`

  const articleQuery = {
    include: {
      coverMedia: true,
      i18n: {
        where: { locale },
        take: 1,
      },
      blocks: {
        orderBy: { order: 'asc' as const },
        take: 20,
      },
    },
  }

  const featuredArticle = await prisma.article.findFirst({
    where: {
      status: ContentStatus.PUBLISHED,
      isFeatured: true,
    },
    ...articleQuery,
  })

  const latestArticles = await prisma.article.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
    },
    ...articleQuery,
    orderBy: { publishedAt: 'desc' },
    take: 8,
  })

  const articleToUse = featuredArticle ?? latestArticles[0] ?? null
  if (!articleToUse) {
    return null
  }

  const articlePool = [articleToUse, ...latestArticles].reduce<typeof latestArticles>((acc, curr) => {
    if (acc.some((a) => a.id === curr.id)) return acc
    return [...acc, curr]
  }, [])

  const toDsArticle = async (article: (typeof latestArticles)[number]): Promise<DsBlogArticle | null> => {
    const i18n = article.i18n[0]
    if (!i18n) return null
    let coverUrl = ''
    if (article.coverMedia?.key) {
      try {
        coverUrl = await getPresignedUrl(article.coverMedia.key)
      } catch {
        coverUrl = ''
      }
    }
    return {
      id: article.id,
      slug: `${blogBasePath}/${article.slug}`,
      title: i18n.title,
      standfirst: i18n.standfirst || '',
      coverUrl,
      authorName: article.authorName,
      publishedAt: article.publishedAt ? article.publishedAt.toISOString() : null,
      readingTime: calculateReadingTime(article.blocks),
    }
  }

  const mapped = (await Promise.all(articlePool.map(toDsArticle))).filter(
    (a): a is DsBlogArticle => a !== null,
  )
  if (mapped.length === 0) return null

  const featured = mapped[0]
  const sidebar = mapped.slice(1, 5)
  const computedTag = eyebrow?.trim()
    ? eyebrow
    : articleToUse.articleType === 'ANALYSIS'
      ? siteCommonCta(locale, 'blog_segment_analysis')
      : articleToUse.isCompanyNews
        ? siteCommonCta(locale, 'blog_segment_company_news')
        : siteCommonCta(locale, 'blog_segment_market_news')

  return (
    <BlogFeaturedModule
      featuredTitle={featured.title}
      featuredHref={featured.slug}
      featuredTag={showEyebrow ? computedTag : ''}
      featuredArticle={featured}
      sideTitle={siteCommonCta(locale, 'blog_featured_stories')}
      sideArticles={sidebar}
      locale={locale}
      showStandfirst={showStandfirst}
      showMeta={showMeta}
      minReadLabel={siteCommonCta(locale, 'blog_min_read')}
      noImageLabel={siteCommonCta(locale, 'no_image')}
      bleedUnderPrimaryNav={bleedUnderPrimaryNav}
    />
  )
}









