import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { Metadata } from 'next'
import { prisma } from '@/lib/prisma'
import { cn } from '@/lib/utils'
import Link from 'next/link'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { Paragraph, SectionTitle, Titlepage, figmaDsLinksClassName } from '@/components/design-system/extracted'
import { getLocaleOrDefault } from '@/config/locales'
import { BlogTemplatePageView } from '@/components/cms/BlogTemplatePageView'
import { parseBlogListingSearchParams } from '@/lib/blog/parseBlogListingSearchParams'
import {
  BlogFeaturedModule,
  BlogRecentPostsModule,
  type DsBlogArticle,
} from '@/components/design-system/Blog/BlogModules'

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams: {} })
  return {
    title: siteCommonCta(locale, 'blog_meta_title'),
    description: siteCommonCta(locale, 'blog_meta_description'),
  }
}

interface ArticlePreview {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  authorName: string
  authorRole: string | null
  publishedAt: string | null
  readingTime: number
  categorySlugs: string[] | null
  articleType?: string
  isCompanyNews?: boolean
}

interface Category {
  id: string
  slug: string
  label: string
}

interface BlogData {
  featured: ArticlePreview | null
  highlighted: ArticlePreview[]
  companyNews: ArticlePreview[]
  articles: ArticlePreview[]
  categories: Category[]
  /** Tags blog (ArticleCategory), préférés aux catégories « offres » pour les filtres. */
  articleCategories: Category[]
  pagination: {
    page: number
    pageSize: number
    hasMore: boolean
  }
}

function categoryLabel(slug: string | undefined | null, data: BlogData): string {
  if (!slug) return ''
  const fromArticle = data.articleCategories.find((c) => c.slug === slug)
  if (fromArticle) return fromArticle.label
  const fromInvestment = data.categories.find((c) => c.slug === slug)
  return fromInvestment?.label || slug
}

function editorialPill(article: ArticlePreview, locale: string): string {
  if (article.articleType === 'ANALYSIS') return siteCommonCta(locale, 'blog_segment_analysis')
  if (article.isCompanyNews) return siteCommonCta(locale, 'blog_segment_company_news')
  return siteCommonCta(locale, 'blog_segment_market_news')
}

async function getBlogData(
  locale: string,
  category?: string,
  page: number = 1,
  segment?: string,
  pageSize: number = 10,
): Promise<BlogData> {
  // Use relative URL for server-side fetch
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'
  const url = new URL('/api/blog', baseUrl)
  url.searchParams.set('locale', locale)
  if (category) {
    url.searchParams.set('category', category)
  }
  if (segment && (segment === 'market' || segment === 'company' || segment === 'analysis')) {
    url.searchParams.set('segment', segment)
  }
  url.searchParams.set('page', page.toString())
  url.searchParams.set('pageSize', String(pageSize))

  try {
    const response = await fetch(url.toString(), {
      cache: 'no-store', // Always fetch fresh data
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Blog API error:', response.status, errorText)
      throw new Error(`Failed to fetch blog data: ${response.status} ${errorText}`)
    }

    return response.json()
  } catch (error) {
    console.error('Error fetching blog data:', error)
    // Return empty data structure on error
    return {
      featured: null,
      highlighted: [],
      companyNews: [],
      articles: [],
      categories: [],
      articleCategories: [],
      pagination: {
        page: 1,
        pageSize: 10,
        hasMore: false,
      },
    }
  }
}

export default async function BlogPage({
  searchParams,
}: {
  searchParams: {
    category?: string | string[]
    page?: string | string[]
    mosaicPage?: string | string[]
    segment?: string | string[]
    locale?: string | string[]
  }
}) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams })

  const { category, pageNum, mosaicPageNum, segment } = parseBlogListingSearchParams(searchParams)

  // Check if a CMS page with template "blog" exists
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'blog' },
  })

  // If CMS page exists with blog template, render via CMS sections
  // The template "blog" uses CMS sections for i18n-ready UI labels
  if (cmsPage && cmsPage.template === 'blog') {
    return (
      <BlogTemplatePageView
        locale={locale}
        category={category}
        pageNum={pageNum}
        mosaicPageNum={mosaicPageNum}
        segment={segment}
        contentStatus="published"
      />
    )
  }

  // Fallback: if no CMS page with blog template, render default blog template
  const data = await getBlogData(locale, category, pageNum, segment, 24)
  const page = pageNum

  const filterCategories =
    data.articleCategories.length > 0 ? data.articleCategories : data.categories

  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`
  const featured = data.featured
  const articleHref = (slug: string) => `${blogBasePath}/${slug}`
  const uniqueArticles = (items: ArticlePreview[]): ArticlePreview[] => {
    const seen = new Set<string>()
    return items.filter((item) => {
      if (seen.has(item.id)) return false
      seen.add(item.id)
      return true
    })
  }
  const sortByMostRecent = (items: ArticlePreview[]): ArticlePreview[] =>
    [...items].sort((a, b) => {
      const aTs = a.publishedAt ? new Date(a.publishedAt).getTime() : 0
      const bTs = b.publishedAt ? new Date(b.publishedAt).getTime() : 0
      return bTs - aTs
    })

  const allPosts = sortByMostRecent(
    uniqueArticles([...(featured ? [featured] : []), ...data.highlighted, ...data.articles, ...data.companyNews]),
  )
  const nonFeaturedPool = sortByMostRecent(
    uniqueArticles([...data.highlighted, ...data.articles, ...data.companyNews]).filter(
      (item) => item.id !== featured?.id,
    ),
  )

  const heroSidebar = !category && page === 1 ? nonFeaturedPool.slice(0, 4) : []
  const recentPosts = !category && page === 1 ? allPosts.slice(0, 3) : nonFeaturedPool.slice(0, 3)
  const categoryFeed = !category && page === 1 ? nonFeaturedPool.slice(7) : nonFeaturedPool

  const categoryBuckets = new Map<string, ArticlePreview[]>()
  for (const article of categoryFeed) {
    const firstSlug = article.categorySlugs?.[0]
    if (!firstSlug) continue
    const list = categoryBuckets.get(firstSlug) ?? []
    list.push(article)
    categoryBuckets.set(firstSlug, list)
  }

  const topCategorySections = filterCategories
    .map((cat) => ({
      ...cat,
      items: categoryBuckets.get(cat.slug) ?? [],
    }))
    .filter((section) => section.items.length > 0)
    .slice(0, 2)

  const toDsArticle = (article: ArticlePreview): DsBlogArticle => ({
    id: article.id,
    slug: articleHref(article.slug),
    title: article.title,
    standfirst: article.standfirst,
    coverUrl: article.coverUrl,
    authorName: article.authorName,
    publishedAt: article.publishedAt,
    readingTime: article.readingTime,
  })

  const renderImage = (article: ArticlePreview, className: string) => {
    if (!article.coverUrl) {
      return (
        <div className={cn('flex items-center justify-center bg-[#d9e2f8] text-[#8893b0]', className)}>
          {siteCommonCta(locale, 'no_image')}
        </div>
      )
    }
    return <img src={article.coverUrl} alt={article.title} className={cn('object-cover', className)} />
  }

  const renderMeta = (article: ArticlePreview) => (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-[#62656e]">
      <span>{article.authorName}</span>
      {article.publishedAt && (
        <>
          <span>•</span>
          <time dateTime={article.publishedAt}>
            {formatArticleDateShort(new Date(article.publishedAt), locale)}
          </time>
        </>
      )}
      <span>•</span>
      <span>
        {article.readingTime} {siteCommonCta(locale, 'blog_min_read')}
      </span>
    </div>
  )

  const segmentLinks = [
    { key: 'market', label: siteCommonCta(locale, 'blog_segment_market_news'), href: blogBasePath },
    {
      key: 'company',
      label: siteCommonCta(locale, 'blog_segment_company_news'),
      href: `${blogBasePath}?segment=company`,
    },
    {
      key: 'analysis',
      label: siteCommonCta(locale, 'blog_segment_analysis'),
      href: `${blogBasePath}?segment=analysis`,
    },
  ] as const

  const categoryQuerySuffix = segment ? `&segment=${segment}` : ''

  return (
    <div className="min-h-screen bg-white pt-20 md:pt-24">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
        <header className="mb-10">
          <Titlepage align="left" className="text-black">
            {siteCommonCta(locale, 'blog_default_title')}
          </Titlepage>
          <Paragraph className="mt-3 max-w-3xl text-[#62656e]">
            {siteCommonCta(locale, 'blog_default_subtitle')}
          </Paragraph>
          <nav className="mt-5 flex flex-wrap gap-2" aria-label={siteCommonCta(locale, 'blog_segments_aria')}>
            {segmentLinks.map((segmentLink) => {
              const isActive =
                (!segment && segmentLink.key === 'market') || segment === segmentLink.key
              return (
                <Link
                  key={segmentLink.key}
                  href={segmentLink.href}
                  className={cn(
                    'rounded-full px-4 py-2 text-sm transition-colors',
                    isActive
                      ? "bg-black text-white font-ui font-semibold"
                      : "bg-[#eff2fb] text-[#62656e] hover:text-black font-ui font-normal",
                  )}
                >
                  {segmentLink.label}
                </Link>
              )
            })}
          </nav>
        </header>

        {filterCategories.length > 0 && (
          <div className="mb-10">
            <nav className="flex flex-wrap gap-2">
              <Link
                href={`${blogBasePath}${segment ? `?segment=${segment}` : ''}`}
                className={cn(
                  'rounded-full px-4 py-2 text-sm transition-colors',
                  !category
                    ? "bg-black text-white font-ui font-semibold"
                    : "bg-[#eff2fb] text-[#62656e] hover:text-black font-ui font-normal",
                )}
              >
                {siteCommonCta(locale, 'blog_filter_all')}
              </Link>
              {filterCategories.map((cat) => (
                <Link
                  key={cat.id}
                  href={`${blogBasePath}?category=${cat.slug}${categoryQuerySuffix}`}
                  className={cn(
                    'rounded-full px-4 py-2 text-sm transition-colors',
                    category === cat.slug
                      ? "bg-black text-white font-ui font-semibold"
                      : "bg-[#eff2fb] text-[#62656e] hover:text-black font-ui font-normal",
                  )}
                >
                  {cat.label}
                </Link>
              ))}
            </nav>
          </div>
        )}

        {featured && !category && page === 1 && (
          <BlogFeaturedModule
            featuredTitle={featured.title}
            featuredHref={articleHref(featured.slug)}
            featuredTag={editorialPill(featured, locale)}
            featuredArticle={toDsArticle(featured)}
            sideTitle={siteCommonCta(locale, 'blog_featured_stories')}
            sideArticles={heroSidebar.map(toDsArticle)}
            locale={locale}
            minReadLabel={siteCommonCta(locale, 'blog_min_read')}
            noImageLabel={siteCommonCta(locale, 'no_image')}
          />
        )}

        {!category && page === 1 && recentPosts.length > 0 && (
          <BlogRecentPostsModule
            title={siteCommonCta(locale, 'blog_latest_articles')}
            ctaLabel="Voir tous les articles"
            ctaHref={blogBasePath}
            articles={recentPosts.map(toDsArticle)}
            locale={locale}
            minReadLabel={siteCommonCta(locale, 'blog_min_read')}
            noImageLabel={siteCommonCta(locale, 'no_image')}
          />
        )}

        {!category &&
          page === 1 &&
          topCategorySections.map((section, index) => (
            <section key={section.id} className="mb-14">
              <div className="mb-5 flex items-center justify-between gap-4">
                <SectionTitle align="left" size="small" className="text-black">
                  {section.label}
                </SectionTitle>
                <Link
                  href={`${blogBasePath}?category=${section.slug}`}
                  className="rounded-full border border-black px-4 py-2 text-[11px] uppercase tracking-[0.08em] text-black hover:bg-black hover:text-white"
                >
                  Lire + d'articles
                </Link>
              </div>

              {index === 0 ? (
                <div className="space-y-5">
                  {section.items.slice(0, 3).map((article) => (
                    <Link key={article.id} href={articleHref(article.slug)} className="grid gap-4 rounded-[10px] border border-[#edf0f8] p-4 md:grid-cols-[1fr_180px]">
                      <div>
                        <h3 className={cn(figmaDsLinksClassName, 'text-[26px] leading-[1.1] text-black')}>
                          {article.title}
                        </h3>
                        <Paragraph className="mt-2 line-clamp-3 text-[#62656e]">{article.standfirst}</Paragraph>
                        {renderMeta(article)}
                      </div>
                      <div className="h-[120px] overflow-hidden rounded-[8px] bg-[#d9e2f8] md:h-full">
                        {renderImage(article, 'h-full w-full')}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {section.items.slice(0, 6).map((article) => (
                    <Link key={article.id} href={articleHref(article.slug)} className="grid grid-cols-[1fr_110px] items-center gap-3 rounded-[10px] border border-[#edf0f8] p-3">
                      <div className="min-w-0">
                        <h3 className={cn(figmaDsLinksClassName, 'line-clamp-2 text-[18px] text-black')}>
                          {article.title}
                        </h3>
                        <Paragraph className="mt-1 line-clamp-2 text-[#62656e]">{article.standfirst}</Paragraph>
                        {renderMeta(article)}
                      </div>
                      <div className="h-[72px] overflow-hidden rounded-[8px] bg-[#d9e2f8]">
                        {renderImage(article, 'h-full w-full')}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          ))}

        {(category || page > 1) && (
          <section>
            <SectionTitle align="left" size="small" className="mb-6 text-black">
              {category
                ? siteCommonCta(locale, 'blog_articles_in_category').replace(
                    '{category}',
                    categoryLabel(category, data),
                  )
                : siteCommonCta(locale, 'blog_latest_articles')}
            </SectionTitle>
            {data.articles.length === 0 ? (
              <Paragraph className="text-[#62656e]">
                {siteCommonCta(locale, 'blog_no_articles_found')}
              </Paragraph>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {data.articles.map((article) => (
                  <Link key={article.id} href={articleHref(article.slug)} className="overflow-hidden rounded-[10px] border border-[#edf0f8]">
                    <div className="h-[180px] overflow-hidden bg-[#d9e2f8]">
                      {renderImage(article, 'h-full w-full')}
                    </div>
                    <div className="p-4">
                      <h3 className={cn(figmaDsLinksClassName, 'line-clamp-2 text-[22px] leading-[1.1] text-black')}>
                        {article.title}
                      </h3>
                      <Paragraph className="mt-2 line-clamp-2 text-[#62656e]">{article.standfirst}</Paragraph>
                      {renderMeta(article)}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        )}

        {data.pagination.hasMore && (
          <div className="mt-10 text-center">
            <Link
              href={`${blogBasePath}${category ? `?category=${category}${categoryQuerySuffix}&` : segment ? `?segment=${segment}&` : '?'}page=${page + 1}`}
              className="inline-block rounded-full bg-black px-6 py-3 text-sm text-white transition-opacity hover:opacity-85"
            >
              {siteCommonCta(locale, 'load_more')}
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
