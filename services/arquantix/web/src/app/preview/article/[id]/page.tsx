import { redirect, notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getSessionFromCookie } from '@/lib/auth'
import { ArticleReadingLayout } from '@/components/layouts/ArticleReadingLayout'
import { getArticleForAdminPreview } from '@/lib/blog/getArticleForAdminPreview'
import { getPageSections, type SectionWithContent } from '@/lib/cms/content'
import { SectionRenderer, type SectionPageRendererContext } from '@/components/cms/SectionRenderer'
import { resolveCanonicalSectionKey, getSectionType } from '@/lib/sections/library'
import { prisma } from '@/lib/prisma'
import { cn } from '@/lib/utils'
import { getLocaleOrDefault } from '@/config/locales'

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

interface PreviewArticlePageProps {
  params: { id: string }
  searchParams?: Record<string, string | string[] | undefined>
}

/**
 * Aperçu admin d'un article (brouillon inclus) pour le split « éditeur ↔ preview live ».
 * Réutilise exactement la chaîne de rendu de `/blog/[slug]/page.tsx` mais sans filtre PUBLISHED.
 * Auth admin obligatoire.
 */
export default async function PreviewArticlePage({
  params,
  searchParams,
}: PreviewArticlePageProps) {
  const session = await getSessionFromCookie()
  if (!session) {
    redirect('/admin/login')
  }

  const cookieStore = await cookies()
  const locale = resolvePublicLocale({
    cookieStore,
    searchParams,
    preferQueryLocaleOverCookie: true,
  })

  const article = await getArticleForAdminPreview(params.id, locale)
  if (!article) {
    notFound()
  }

  // Sections du gabarit `article` : on essaie d'abord en draft, fallback en published si vide.
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'article' },
  })

  let rawSections: SectionWithContent[] = []
  if (cmsPage && cmsPage.template === 'article') {
    rawSections = await getPageSections('article', locale, 'draft')
    if (rawSections.length === 0) {
      rawSections = await getPageSections('article', locale, 'published')
    }
  }

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
  )
}
