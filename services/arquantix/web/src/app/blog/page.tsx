import { cookies } from 'next/headers'
import { getLocaleFromCookies } from '@/lib/i18n/locale-server'
import { defaultLocale } from '@/config/locales'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'
import { Navigation } from '@/components/sections/Navigation'
import { Metadata } from 'next'
import { prisma } from '@/lib/prisma'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import Link from 'next/link'
import { formatArticleDateShort } from '@/lib/blog/formatDates'

export const metadata: Metadata = {
  title: 'Blog — Vancelian',
  description: 'Actualités de l’entreprise, analyses et perspectives Vancelian.',
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

function editorialPill(article: ArticlePreview): string {
  if (article.articleType === 'ANALYSIS') return 'Analysis'
  if (article.isCompanyNews) return 'Company News'
  return 'Market News'
}

async function getBlogData(
  locale: string,
  category?: string,
  page: number = 1,
  segment?: string
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
  searchParams: { category?: string; page?: string; segment?: string }
}) {
  const cookieStore = await cookies()
  const locale = await getLocaleFromCookies(cookieStore) || defaultLocale
  const menuItems = await getPrimaryMenu(locale)

  // Check if a CMS page with template "blog" exists
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'blog' },
  })

  // Get theme color from CMS page or default to 'light' for blog
  const themeColor = (cmsPage?.themeColor && (cmsPage.themeColor === 'dark' || cmsPage.themeColor === 'light')) 
    ? cmsPage.themeColor as 'dark' | 'light'
    : 'light'

  // If CMS page exists with blog template, render via CMS sections
  // The template "blog" uses CMS sections for i18n-ready UI labels
  if (cmsPage && cmsPage.template === 'blog') {
    // Get sections from CMS
    const sections = await getPageSections('blog', locale, 'published')
    const category = searchParams.category
    const pageNum = parseInt(searchParams.page || '1')

    if (sections.length === 0) {
      // Fallback if no sections configured
      return (
        <>
          <Navigation menuItems={menuItems} themeColor={themeColor} />
          <div className="min-h-screen bg-white pt-20 md:pt-24">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
              <div className="text-center py-12">
                <p className="text-gray-500">Blog page is not configured. Please add sections in the admin.</p>
              </div>
            </div>
          </div>
        </>
      )
    }

    return (
      <>
        <Navigation menuItems={menuItems} themeColor={themeColor} />
        <div className="min-h-screen bg-white pt-20 md:pt-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            {sections.map((section) => (
              <SectionRenderer
                key={section.id}
                section={section}
                locale={locale}
                category={category}
                page={pageNum}
              />
            ))}
          </div>
        </div>
      </>
    )
  }

  // Fallback: if no CMS page with blog template, render default blog template
  const category = searchParams.category
  const page = parseInt(searchParams.page || '1')
  const segment = searchParams.segment

  const data = await getBlogData(locale, category, page, segment)

  const filterCategories =
    data.articleCategories.length > 0 ? data.articleCategories : data.categories

  return (
    <>
      <Navigation menuItems={menuItems} themeColor={themeColor} />
      <div className="min-h-screen bg-white pt-20 md:pt-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <header className="mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">Blog</h1>
            <p className="text-lg text-gray-600">
              Actualités Vancelian, analyses marché et perspectives du groupe.
            </p>
            <nav className="mt-6 flex flex-wrap gap-2" aria-label="Editorial segments">
              <Link
                href="/blog"
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  !segment || segment === 'market'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Market News
              </Link>
              <Link
                href="/blog?segment=company"
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  segment === 'company'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Company News
              </Link>
              <Link
                href="/blog?segment=analysis"
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  segment === 'analysis'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Analysis
              </Link>
            </nav>
          </header>

          {/* Categories Navigation (tags ArticleCategory si disponibles) */}
          {filterCategories.length > 0 && (
            <div className="mb-12">
              <nav className="flex flex-wrap gap-2">
                <Link
                  href="/blog"
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    !category
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Tout
                </Link>
                {filterCategories.map((cat) => (
                  <Link
                    key={cat.id}
                    href={`/blog?category=${cat.slug}`}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      category === cat.slug
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {cat.label}
                  </Link>
                ))}
              </nav>
            </div>
          )}

          {/* Featured Article Hero */}
          {data.featured && !category && page === 1 && (
            <div className="mb-16">
              <Link
                href={`/blog/${data.featured.slug}`}
                className="group block bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
              >
                <div className="grid md:grid-cols-2 gap-0 md:items-stretch">
                  <div className="aspect-video md:aspect-auto overflow-hidden bg-gray-100 relative">
                    {data.featured.coverUrl ? (
                      <img
                        src={data.featured.coverUrl}
                        alt={data.featured.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        No image
                      </div>
                    )}
                  </div>
                  <div className="p-8 md:p-12 flex flex-col justify-center bg-white">
                    <div className="mb-4 flex flex-wrap gap-2">
                      <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
                        {editorialPill(data.featured)}
                      </span>
                      {data.featured.categorySlugs && data.featured.categorySlugs.length > 0 && (
                        <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold">
                          {categoryLabel(data.featured!.categorySlugs![0], data)}
                        </span>
                      )}
                    </div>
                    <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 group-hover:text-indigo-600 transition-colors">
                      {data.featured.title}
                    </h2>
                    <p className="text-lg text-gray-600 mb-6 line-clamp-3 leading-relaxed">{data.featured.standfirst}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="font-semibold">{data.featured.authorName}</span>
                      {data.featured.publishedAt && (
                        <time dateTime={data.featured.publishedAt}>
                          {formatArticleDateShort(new Date(data.featured.publishedAt), locale)}
                        </time>
                      )}
                      <span>•</span>
                      <span>{data.featured.readingTime} min read</span>
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          )}

          {/* Highlighted Mosaic */}
          {data.highlighted.length > 0 && !category && page === 1 && (
            <div className="mb-16">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Featured Stories</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {data.highlighted.map((article, index) => (
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
                      {article.categorySlugs && article.categorySlugs.length > 0 && (
                        <div className="mb-2">
                          <span className="text-xs text-indigo-600 font-semibold uppercase tracking-wide">
                            {categoryLabel(article.categorySlugs![0], data)}
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
                            <span>•</span>
                            <time dateTime={article.publishedAt}>
                              {formatArticleDateShort(new Date(article.publishedAt), locale)}
                            </time>
                          </>
                        )}
                        <span>•</span>
                        <span>{article.readingTime} min read</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* News entreprise Vancelian */}
          {data.companyNews.length > 0 &&
            !category &&
            page === 1 &&
            (!segment || segment === 'market') && (
            <section
              className="mb-16 rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/90 to-white p-6 shadow-sm md:p-10"
              aria-labelledby="vancelian-company-news-heading"
            >
              <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                    Vancelian
                  </p>
                  <h2
                    id="vancelian-company-news-heading"
                    className="text-2xl font-bold tracking-tight text-gray-900 md:text-3xl"
                  >
                    Actualités de l&apos;entreprise
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm text-gray-600">
                    Communiqués officiels, réglementation et annonces du groupe — distinct des contenus
                    éditoriaux généraux.
                  </p>
                </div>
                <Link
                  href="/blog?segment=company"
                  className="shrink-0 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  Fil Company News →
                </Link>
              </div>
              <div className="grid gap-6 md:grid-cols-2">
                {data.companyNews.map((article) => (
                  <Link
                    key={article.id}
                    href={`/blog/${article.slug}`}
                    className="group flex flex-col overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div className="aspect-[16/9] overflow-hidden bg-gray-100">
                      {article.coverUrl ? (
                        <img
                          src={article.coverUrl}
                          alt=""
                          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-gray-400">
                          —
                        </div>
                      )}
                    </div>
                    <div className="flex flex-1 flex-col p-5">
                      {article.categorySlugs && article.categorySlugs.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1">
                          {article.categorySlugs.slice(0, 3).map((slug) => (
                            <span
                              key={slug}
                              className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-800"
                            >
                              {categoryLabel(slug, data)}
                            </span>
                          ))}
                        </div>
                      )}
                      <h3 className="text-lg font-semibold leading-snug text-gray-900 group-hover:text-indigo-700">
                        {article.title}
                      </h3>
                      <p className="mt-2 line-clamp-2 text-sm text-gray-600">{article.standfirst}</p>
                      <div className="mt-auto pt-4 text-xs text-gray-500">
                        <span className="font-medium text-gray-700">{article.authorName}</span>
                        {article.publishedAt && (
                          <>
                            <span className="mx-2">·</span>
                            <time dateTime={article.publishedAt}>
                              {formatArticleDateShort(new Date(article.publishedAt), locale)}
                            </time>
                          </>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Main Feed */}
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              {category
                ? `Articles : ${categoryLabel(category, data)}`
                : 'Derniers articles'}
            </h2>
            {data.articles.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">No articles found.</p>
              </div>
            ) : (
              <>
                <div className="space-y-8">
                  {data.articles.map((article) => (
                    <Link
                      key={article.id}
                      href={`/blog/${article.slug}`}
                      className="group block bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
                    >
                      <div className="grid md:grid-cols-3 gap-0">
                        <div className="md:col-span-1 aspect-video md:aspect-auto md:h-48 overflow-hidden bg-gray-100">
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
                        <div className="md:col-span-2 p-6">
                          {article.categorySlugs && article.categorySlugs.length > 0 && (
                            <div className="mb-2">
                              <span className="inline-block px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-semibold">
                                {categoryLabel(article.categorySlugs![0], data)}
                              </span>
                            </div>
                          )}
                          <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                            {article.title}
                          </h3>
                          <p className="text-gray-600 text-sm mb-4 line-clamp-2">{article.standfirst}</p>
                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span className="font-medium">{article.authorName}</span>
                            {article.publishedAt && (
                              <time dateTime={article.publishedAt}>
                                {formatArticleDateShort(new Date(article.publishedAt), locale)}
                              </time>
                            )}
                            <span>•</span>
                            <span>{article.readingTime} min read</span>
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>

                {/* Pagination */}
                {data.pagination.hasMore && (
                  <div className="mt-12 text-center">
                    <Link
                      href={`/blog${category ? `?category=${category}&` : '?'}page=${page + 1}`}
                      className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                    >
                      Load More
                    </Link>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
