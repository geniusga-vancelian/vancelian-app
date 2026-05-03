import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { notFound } from 'next/navigation'
import { Metadata } from 'next'
import { cookies } from 'next/headers'
import { ArticleReadingLayout } from '@/components/layouts/ArticleReadingLayout'
import { getPublicArticle } from '@/lib/blog/getPublicArticle'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer, type SectionPageRendererContext } from '@/components/cms/SectionRenderer'
import { resolveCanonicalSectionKey, getSectionType } from '@/lib/sections/library'
import { prisma } from '@/lib/prisma'
import { cn } from '@/lib/utils'
import { getLocaleOrDefault } from '@/config/locales'
import type { SectionWithContent } from '@/lib/cms/content'

const ALLOWED_ARTICLE_SECTIONS = new Set([
  'blog_article_reader',
  'blog_article_hero',
  'share_sm',
  'blog_article_related',
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

const FULL_BLEED = new Set(['cta', 'key_figures'])

function withFallbackReader(
  sections: SectionWithContent[],
  locale: string,
): SectionWithContent[] {
  const hasReader = sections.some(
    (s) => (resolveCanonicalSectionKey(s.key) ?? s.key) === 'blog_article_reader',
  )
  if (hasReader) return sections
  const t = getSectionType('blog_article_reader')
  if (!t) return sections
  const loc = getLocaleOrDefault(locale)
  const fallback: SectionWithContent = {
    id: 'fallback-blog-article-reader',
    key: 'blog_article_reader',
    order: -100,
    schemaVersion: t.schemaVersion,
    data: t.defaultData,
    locale: loc,
    status: 'PUBLISHED',
  }
  return [fallback, ...sections].sort((a, b) => a.order - b.order)
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { slug: string }
  searchParams?: Record<string, string | string[] | undefined>
}): Promise<Metadata> {
  try {
    const cookieStore = await cookies()
    const locale = resolvePublicLocale({ cookieStore, searchParams })
    const article = await getPublicArticle(params.slug, locale)

    if (!article) {
      return { title: 'Article not found' }
    }

    const coverUrl = article.coverUrl

    return {
      title: article.i18n.metaTitle || article.i18n.title,
      description: article.i18n.metaDescription || article.i18n.standfirst,
      openGraph: {
        title: article.i18n.metaTitle || article.i18n.title,
        description: article.i18n.metaDescription || article.i18n.standfirst,
        images: coverUrl ? [{ url: coverUrl }] : [],
        type: 'article',
        publishedTime: article.publishedAt ? article.publishedAt.toISOString() : undefined,
        authors: [article.authorName],
      },
      twitter: {
        card: 'summary_large_image',
        title: article.i18n.metaTitle || article.i18n.title,
        description: article.i18n.metaDescription || article.i18n.standfirst,
        images: coverUrl ? [coverUrl] : [],
      },
    }
  } catch (error) {
    console.error('Error generating metadata for article:', error)
    return { title: 'Article', description: 'Article page' }
  }
}

export default async function ArticlePage({
  params,
  searchParams,
}: {
  params: { slug: string }
  searchParams?: Record<string, string | string[] | undefined>
}) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams })
  const article = await getPublicArticle(params.slug, locale)

  if (!article) {
    notFound()
  }

  const isVancelianCompanyNews = article.isCompanyNews === true

  const schemaOrg = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.i18n.title,
    description: article.i18n.standfirst,
    image: article.coverUrl,
    datePublished: article.publishedAt,
    dateModified: article.updatedAt,
    author: {
      '@type': 'Person',
      name: article.authorName,
      jobTitle: article.authorRole || undefined,
    },
    publisher: {
      '@type': 'Organization',
      name: isVancelianCompanyNews ? 'Vancelian' : 'Arquantix',
      ...(isVancelianCompanyNews ? { url: 'https://www.vancelian.com' } : {}),
    },
  }

  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'article' },
  })

  const rawSections =
    cmsPage && cmsPage.template === 'article'
      ? await getPageSections('article', locale, 'published')
      : []

  const filtered = withFallbackReader(
    rawSections.filter((section) => {
      const c = resolveCanonicalSectionKey(section.key) ?? section.key
      return ALLOWED_ARTICLE_SECTIONS.has(c)
    }),
    locale,
  )

  const hasReader = filtered.some(
    (s) => (resolveCanonicalSectionKey(s.key) ?? s.key) === 'blog_article_reader',
  )
  const shareSmSection =
    filtered.find((s) => (resolveCanonicalSectionKey(s.key) ?? s.key) === 'share_sm') ?? null
  const sectionsToRender = filtered.filter((s) => {
    const c = resolveCanonicalSectionKey(s.key) ?? s.key
    if (c === 'share_sm' && hasReader) return false
    return true
  })
  const rendererContext: SectionPageRendererContext = {
    shareSmSection: hasReader ? shareSmSection : null,
  }

  const firstCanonical =
    sectionsToRender.length > 0
      ? resolveCanonicalSectionKey(sectionsToRender[0]!.key) ?? sectionsToRender[0]!.key
      : null
  const blogArticleHeroBleedsUnderNav = firstCanonical === 'blog_article_hero'

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrg) }}
      />
      <ArticleReadingLayout suppressHeaderOffset={blogArticleHeroBleedsUnderNav}>
        {sectionsToRender.map((section, index) => {
          const c = resolveCanonicalSectionKey(section.key) ?? section.key
          const isFullBleed = FULL_BLEED.has(c)
          const sectionHasOwnMaxWidth =
            c === 'blog_article_reader' ||
            c === 'blog_article_hero' ||
            c === 'blog_article_related'
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
                blogArticle={article}
                rendererContext={rendererContext}
                blogHeroBleedUnderNav={blogArticleHeroBleedsUnderNav && index === 0}
              />
            </div>
          )
        })}
      </ArticleReadingLayout>
    </>
  )
}
