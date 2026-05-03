import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { defaultLocale, getLocaleOrDefault, type Locale } from '@/config/locales'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { ArticleReadingLayout } from '@/components/layouts/ArticleReadingLayout'
import { ArticleCarousel } from '@/components/blog/ArticleCarousel'
import Link from 'next/link'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getDateLabels, formatArticleDate } from '@/lib/blog/formatDates'
import ReactMarkdown from 'react-markdown'
import {
  getExclusiveOfferVaultPayload,
  type ExclusiveOfferVaultPayload,
} from '@/lib/cms/exclusiveOfferVaultPage'
import { ExclusiveOfferVaultDetail } from '@/components/exclusive-offer/ExclusiveOfferVaultDetail'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { getPageSections, type SectionWithContent } from '@/lib/cms/content'
import { SectionRenderer, type SectionPageRendererContext } from '@/components/cms/SectionRenderer'
import { resolveCanonicalSectionKey, getSectionType } from '@/lib/sections/library'
import { cn } from '@/lib/utils'

export type ProjectDetailSharedProps = {
  slug: string
  searchParams: Record<string, string | string[] | undefined>
  /** Locale issue de l’URL (`/[locale]/projects/...`) — prioritaire dans resolvePublicLocale. */
  urlLocale?: string | null
}

const ALLOWED_EXCLUSIVE_OFFER_GABARIT_SECTIONS = new Set([
  'exclusive_offer_vault',
  'share_sm',
  'cta',
  'key_figures',
  'faq',
  'media_text',
  'testimonials',
  'how_it_works',
  'figma_simple_hero',
  'figma_stats_grid',
  'figma_testimonial_cards',
  'company_map',
  'hero_secondary',
])

const FULL_BLEED_OFFER_GABARIT = new Set(['cta', 'key_figures'])

function withFallbackExclusiveOfferVault(
  sections: SectionWithContent[],
  locale: string,
): SectionWithContent[] {
  const hasVault = sections.some(
    (s) => (resolveCanonicalSectionKey(s.key) ?? s.key) === 'exclusive_offer_vault',
  )
  if (hasVault) return sections
  const t = getSectionType('exclusive_offer_vault')
  if (!t) return sections
  const loc = getLocaleOrDefault(locale)
  const fallback: SectionWithContent = {
    id: 'fallback-exclusive-offer-vault',
    key: 'exclusive_offer_vault',
    order: -100,
    schemaVersion: t.schemaVersion,
    data: t.defaultData,
    locale: loc,
    status: 'PUBLISHED',
  }
  return [fallback, ...sections].sort((a, b) => a.order - b.order)
}

async function renderExclusiveOfferPageWithGabarit(
  vaultPayload: ExclusiveOfferVaultPayload,
  locale: Locale,
): Promise<ReactNode> {
  const cmsPage = await prisma.page.findUnique({
    where: { slug: EXCLUSIVE_OFFER_GABARIT_SLUG },
    select: { template: true },
  })
  if (!cmsPage || cmsPage.template !== EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
    return <ExclusiveOfferVaultDetail payload={vaultPayload} />
  }

  const rawSections = await getPageSections(EXCLUSIVE_OFFER_GABARIT_SLUG, locale, 'published')
  const filtered = withFallbackExclusiveOfferVault(
    rawSections.filter((section) => {
      const c = resolveCanonicalSectionKey(section.key) ?? section.key
      return ALLOWED_EXCLUSIVE_OFFER_GABARIT_SECTIONS.has(c)
    }),
    locale,
  )

  if (filtered.length === 0) {
    return <ExclusiveOfferVaultDetail payload={vaultPayload} />
  }

  const rendererContext: SectionPageRendererContext = {}

  return (
    <>
      {filtered.map((section) => {
        const c = resolveCanonicalSectionKey(section.key) ?? section.key
        const isFullBleed = FULL_BLEED_OFFER_GABARIT.has(c)
        const sectionHasOwnMaxWidth = c === 'exclusive_offer_vault'
        return (
          <div
            key={section.id}
            className={cn(
              !isFullBleed &&
                !sectionHasOwnMaxWidth &&
                'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8',
            )}
          >
            <SectionRenderer
              section={section}
              locale={locale}
              exclusiveOfferVaultPayload={vaultPayload}
              rendererContext={rendererContext}
            />
          </div>
        )
      })}
    </>
  )
}

export async function generateProjectDetailPageMetadata({
  slug,
}: {
  slug: string
}): Promise<Metadata> {
  const page = await prisma.page.findUnique({
    where: { slug },
    select: { template: true, title: true, description: true },
  })
  if (!page || page.template !== VAULT_BUILDER_TEMPLATE) {
    return {}
  }
  return {
    title: page.title?.trim() || 'Offre',
    description: page.description?.trim() || undefined,
  }
}

export async function projectDetailPageContent({
  slug,
  searchParams,
  urlLocale,
}: ProjectDetailSharedProps) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams, urlLocale })

  if (slug === EXCLUSIVE_OFFER_GABARIT_SLUG) {
    notFound()
  }

  const vaultPage = await prisma.page.findUnique({
    where: { slug },
    select: { template: true },
  })
  if (vaultPage?.template === VAULT_BUILDER_TEMPLATE) {
    const vaultPayload = await getExclusiveOfferVaultPayload(slug, locale)
    if (!vaultPayload) {
      notFound()
    }
    return renderExclusiveOfferPageWithGabarit(vaultPayload, locale)
  }

  // Fetch published project
  const project = await prisma.project.findUnique({
    where: {
      slug,
      status: ContentStatus.PUBLISHED,
    },
    include: {
      coverMedia: true,
      heroMedia: true,
      i18n: {
        where: {
          locale,
        },
        take: 1,
      },
      projectMedia: {
        include: {
          media: true,
        },
        orderBy: { order: 'asc' },
      },
    },
  })

  if (!project) {
    notFound()
  }

  // Fallback to default locale if no i18n for requested locale
  let i18n = project.i18n[0] || null
  if (!i18n && locale !== defaultLocale) {
    const defaultI18n = await prisma.projectI18n.findFirst({
      where: {
        projectId: project.id,
        locale: defaultLocale,
      },
    })
    if (defaultI18n) {
      i18n = defaultI18n
    }
  }

  if (!i18n) {
    notFound()
  }

  const lendingProduct = await prisma.lendingPoolProducts.findUnique({
    where: { projectId: project.id },
  })

  // Resolve hero media URL (prefer heroMedia over coverMedia for detail page)
  let heroUrl = project.heroMedia?.url || project.coverMedia?.url || null
  if (project.heroMedia) {
    try {
      heroUrl = await getPresignedUrl(project.heroMedia.key, 3600)
    } catch (error) {
      console.error(`Failed to get presigned URL for ${project.heroMedia.key}:`, error)
      heroUrl = project.heroMedia.url
    }
  } else if (project.coverMedia) {
    try {
      heroUrl = await getPresignedUrl(project.coverMedia.key, 3600)
    } catch (error) {
      console.error(`Failed to get presigned URL for ${project.coverMedia.key}:`, error)
      heroUrl = project.coverMedia.url
    }
  }

  // Resolve gallery media URLs
  const galleryWithUrls = await Promise.all(
    project.projectMedia.map(async (item) => {
      try {
        const url = await getPresignedUrl(item.media.key, 3600)
        return {
          ...item,
          media: {
            ...item.media,
            url,
          },
        }
      } catch (error) {
        console.error(`Failed to get presigned URL for ${item.media.key}:`, error)
        return item
      }
    })
  )

  // Extract YouTube video ID from URL
  const getYouTubeVideoId = (url: string | null): string | null => {
    if (!url) return null
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
    return match ? match[1] : null
  }

  const youtubeVideoId = getYouTubeVideoId(project.youtubeUrl)

  // Fetch articles linked to this project via ArticleProject
  // First, get article IDs linked to this project
  const articleProjects = await prisma.articleProject.findMany({
    where: {
      projectId: project.id,
    },
    select: {
      articleId: true,
    },
    orderBy: { createdAt: 'desc' },
    take: 3,
  })

  const articleIds = articleProjects.map((ap) => ap.articleId)

  // Then fetch the articles with their data
  const articlesWithProjectTag = articleIds.length > 0
    ? await prisma.article.findMany({
        where: {
          id: { in: articleIds },
          status: ContentStatus.PUBLISHED,
        },
        include: {
          coverMedia: true,
          i18n: {
            where: { locale },
            take: 1,
          },
        },
        orderBy: { publishedAt: 'desc' },
      })
    : []

  // Resolve article URLs and filter out those without i18n
  const articlesWithUrls = await Promise.all(
    articlesWithProjectTag.map(async (article) => {
      let coverUrl = article.coverMedia?.url || ''
      if (article.coverMedia?.key) {
        try {
          coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
        } catch {
          // Fallback to original URL
        }
      }

      const i18n = article.i18n[0]
      if (!i18n) return null

      return {
        id: article.id,
        slug: article.slug,
        title: i18n.title,
        standfirst: i18n.standfirst,
        coverUrl,
        publishedAt: article.publishedAt,
        authorName: article.authorName,
      }
    })
  )

  const latestNews = articlesWithUrls.filter((a): a is NonNullable<typeof a> => a !== null)

  // ── Offre exclusive : même gabarit que le blog (ArticleReadingLayout) ──
  if (lendingProduct) {
    const updatedDate = new Date(project.updatedAt)
    const dateLabels = getDateLabels(locale)
    const supplyAprPct = Number(lendingProduct.supplyAprBps) / 100
    const raised = Number(lendingProduct.currentRaised)
    const target = Number(lendingProduct.targetSize)
    const progressPct = target > 0 ? Math.min(100, (raised / target) * 100) : 0

    const galleryImageUrls = galleryWithUrls.map((g) => g.media.url).filter(Boolean)
    const carouselImages =
      galleryImageUrls.length > 0
        ? heroUrl
          ? [heroUrl, ...galleryImageUrls]
          : galleryImageUrls
        : heroUrl
          ? [heroUrl]
          : []

    const showMediaBlock =
      Boolean(youtubeVideoId) || carouselImages.length > 0

    const statusLabel = lendingProduct.status.replace(/_/g, ' ')

    return (
      <>
        <ArticleReadingLayout>
          <header className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 pt-12 pb-8">
            <div className="text-sm text-gray-500 mb-6 space-y-1">
              <div>
                {dateLabels.updated}{' '}
                <time dateTime={updatedDate.toISOString()}>
                  {formatArticleDate(updatedDate, locale)}
                </time>
              </div>
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
                Exclusive offer
              </span>
              <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
                {lendingProduct.asset}
              </span>
              <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-900 capitalize">
                {statusLabel}
              </span>
            </div>

            <h1 className="text-[2.75rem] md:text-[2.75rem] font-bold text-gray-900 mb-6 leading-tight tracking-tight">
              {i18n.title}
            </h1>
            {i18n.shortDescription && (
              <p className="text-xl md:text-2xl text-gray-700 italic mb-8 leading-relaxed">
                {i18n.shortDescription}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-base text-gray-600 border-t border-gray-200 pt-6">
              <span className="font-semibold text-gray-900">
                {supplyAprPct.toFixed(2)}% APR (supply)
              </span>
              <span className="text-gray-400">•</span>
              <span>
                {raised.toLocaleString(locale)} / {target.toLocaleString(locale)}{' '}
                {lendingProduct.asset}
              </span>
              <span className="text-gray-400">•</span>
              <span>{progressPct.toFixed(1)}% funded</span>
            </div>
          </header>

          {showMediaBlock && (
            <div className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 mb-12">
              {youtubeVideoId ? (
                <div className="relative aspect-video bg-black rounded overflow-hidden">
                  <iframe
                    src={`https://www.youtube.com/embed/${youtubeVideoId}`}
                    title={i18n.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    className="w-full h-full"
                  />
                </div>
              ) : carouselImages.length > 1 ? (
                <ArticleCarousel images={carouselImages} title={i18n.title} />
              ) : carouselImages.length === 1 ? (
                <div className="relative">
                  <img
                    src={carouselImages[0]}
                    alt={i18n.title}
                    className="w-full h-auto"
                  />
                </div>
              ) : null}
            </div>
          )}

          <div className="max-w-[1280px] mx-auto pb-16">
            <div className="flex flex-col lg:flex-row">
              <div className="flex-1 max-w-[960px] mx-auto px-4 sm:px-8 md:px-16">
                <div className="text-lg leading-[1.75] text-gray-800 space-y-8">
                  {i18n.description && (
                    <div className="prose prose-lg max-w-none prose-headings:text-gray-900 prose-p:text-gray-800">
                      <ReactMarkdown>{i18n.description}</ReactMarkdown>
                    </div>
                  )}

                  {galleryWithUrls.length > 0 && !showMediaBlock && (
                    <div>
                      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Portfolio</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {galleryWithUrls.map((item) => (
                          <div
                            key={item.id}
                            className="relative aspect-[4/3] overflow-hidden rounded-lg group border border-gray-100 shadow-sm"
                          >
                            <img
                              src={item.media.url}
                              alt={item.media.alt || i18n.title}
                              className="w-full h-full object-cover transition-transform group-hover:scale-105"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {latestNews.length > 0 && (
            <div className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 mt-8 pb-12 border-t border-gray-200 pt-12">
              <h2 className="text-2xl font-bold text-gray-900 mb-8">Latest news</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {latestNews.map((article) => (
                  <Link
                    key={article.id}
                    href={`/${locale}/blog/${article.slug}`}
                    className="group bg-gray-50 rounded-lg overflow-hidden hover:bg-gray-100 transition-colors border border-gray-100"
                  >
                    <div className="aspect-video w-full overflow-hidden bg-gray-200">
                      {article.coverUrl ? (
                        <img
                          src={article.coverUrl}
                          alt={article.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                          No image
                        </div>
                      )}
                    </div>
                    <div className="p-6">
                      <h3 className="text-xl font-semibold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                        {article.title}
                      </h3>
                      <p className="text-gray-600 text-sm mb-4 line-clamp-3">{article.standfirst}</p>
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>{article.authorName}</span>
                        {article.publishedAt && (
                          <time
                            dateTime={
                              article.publishedAt instanceof Date
                                ? article.publishedAt.toISOString()
                                : String(article.publishedAt)
                            }
                          >
                            {new Date(article.publishedAt).toLocaleDateString(
                              locale === 'fr' ? 'fr-FR' : 'en-US',
                              {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                              }
                            )}
                          </time>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </ArticleReadingLayout>
      </>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <main>
        {/* Hero Section with Hero Image */}
        {heroUrl && (
          <div className="relative h-[500px] overflow-hidden">
            <img
              src={heroUrl}
              alt={i18n.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/50" />
            <div className="absolute inset-0 flex items-center justify-center">
              <h1 className="text-4xl md:text-5xl font-bold text-center px-4">
                {i18n.title}
              </h1>
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          {/* Title (if no hero image) */}
          {!heroUrl && (
            <h1 className="text-4xl font-bold mb-8">{i18n.title}</h1>
          )}

          {/* Short Description */}
          {i18n.shortDescription && (
            <p className="text-xl text-gray-300 mb-8">{i18n.shortDescription}</p>
          )}

          {/* YouTube Video */}
          {youtubeVideoId && (
            <div className="mb-12">
              <div className="aspect-video w-full">
                <iframe
                  src={`https://www.youtube.com/embed/${youtubeVideoId}`}
                  title={i18n.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="w-full h-full rounded-lg"
                />
              </div>
            </div>
          )}

          {/* Description (Markdown - V1: simple text rendering) */}
          {i18n.description && (
            <div className="prose prose-invert max-w-none mb-12">
              <div className="whitespace-pre-wrap text-gray-300 leading-relaxed">
                {i18n.description}
              </div>
            </div>
          )}

          {/* Portfolio Gallery */}
          {galleryWithUrls.length > 0 && (
            <div className="mb-12">
              <h2 className="text-2xl font-semibold mb-6">Portfolio</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {galleryWithUrls.map((item) => (
                  <div key={item.id} className="relative aspect-[4/3] overflow-hidden rounded-lg group">
                    <img
                      src={item.media.url}
                      alt={item.media.alt || i18n.title}
                      className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Latest News Section */}
          {latestNews.length > 0 && (
            <div className="mt-16 border-t border-gray-800 pt-12">
              <h2 className="text-3xl font-bold mb-8">Latest news</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {latestNews.map((article) => (
                  <Link
                    key={article.id}
                    href={`/${locale}/blog/${article.slug}`}
                    className="group bg-gray-900 rounded-lg overflow-hidden hover:bg-gray-800 transition-colors"
                  >
                    <div className="aspect-video w-full overflow-hidden bg-gray-800">
                      {article.coverUrl ? (
                        <img
                          src={article.coverUrl}
                          alt={article.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-600">
                          No image
                        </div>
                      )}
                    </div>
                    <div className="p-6">
                      <h3 className="text-xl font-semibold text-white mb-2 group-hover:text-indigo-400 transition-colors">
                        {article.title}
                      </h3>
                      <p className="text-gray-400 text-sm mb-4 line-clamp-3">{article.standfirst}</p>
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>{article.authorName}</span>
                        {article.publishedAt && (
                          <time dateTime={article.publishedAt instanceof Date ? article.publishedAt.toISOString() : article.publishedAt}>
                            {new Date(article.publishedAt).toLocaleDateString('fr-FR', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                            })}
                          </time>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

