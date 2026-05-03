import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { ArticleReadingLayout } from '@/components/layouts/ArticleReadingLayout'
import { GabaritPreviewPlaceholder } from '@/components/cms/GabaritPreviewPlaceholder'
import { SectionRenderer, type SectionPageRendererContext } from '@/components/cms/SectionRenderer'
import { getPageSections, type SectionWithContent } from '@/lib/cms/content'
import {
  EXCLUSIVE_OFFER_GABARIT_SLUG,
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { prisma } from '@/lib/prisma'
import { isValidLocale, type Locale } from '@/config/locales'
import { getLocaleOrDefault } from '@/config/locales'
import { resolveCanonicalSectionKey, getSectionType } from '@/lib/sections/library'
import { cn } from '@/lib/utils'

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

const FULL_BLEED_ARTICLE = new Set(['cta', 'key_figures'])
const FULL_BLEED_OFFER_GABARIT = new Set(['cta', 'key_figures'])

function withFallbackReader(sections: SectionWithContent[], locale: string): SectionWithContent[] {
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

type Props = { params: { locale: string; slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  if (!isValidLocale(params.locale)) {
    return { title: 'Aperçu gabarit' }
  }
  return {
    title: 'Aperçu gabarit CMS',
    robots: { index: false, follow: false },
  }
}

export default async function GabaritPreviewPage({ params }: Props) {
  const { locale: localeParam, slug } = params
  if (!isValidLocale(localeParam)) {
    notFound()
  }
  const locale = localeParam as Locale

  const page = await prisma.page.findUnique({
    where: { slug },
    select: { template: true },
  })
  if (!page) {
    notFound()
  }

  if (slug === 'article') {
    if (page.template !== 'article') {
      notFound()
    }

    const rawSections = await getPageSections('article', locale, 'published')
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

    const firstCanonicalArticle =
      sectionsToRender.length > 0
        ? resolveCanonicalSectionKey(sectionsToRender[0]!.key) ?? sectionsToRender[0]!.key
        : null
    const blogArticleHeroBleedsUnderNav = firstCanonicalArticle === 'blog_article_hero'

    return (
      <ArticleReadingLayout suppressHeaderOffset={blogArticleHeroBleedsUnderNav}>
        {sectionsToRender.map((section, index) => {
          const c = resolveCanonicalSectionKey(section.key) ?? section.key
          const isFullBleed = FULL_BLEED_ARTICLE.has(c)
          const sectionHasOwnMaxWidth =
            c === 'blog_article_reader' ||
            c === 'blog_article_hero' ||
            c === 'blog_article_related'

          if (c === 'blog_article_reader') {
            return (
              <div
                key={section.id}
                className={cn(
                  !isFullBleed &&
                    !sectionHasOwnMaxWidth &&
                    'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8',
                )}
              >
                <GabaritPreviewPlaceholder variant="article" />
              </div>
            )
          }

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
                rendererContext={rendererContext}
                blogHeroBleedUnderNav={blogArticleHeroBleedsUnderNav && index === 0}
              />
            </div>
          )
        })}
      </ArticleReadingLayout>
    )
  }

  if (slug === EXCLUSIVE_OFFER_GABARIT_SLUG) {
    if (page.template !== EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
      notFound()
    }

    const rawSections = await getPageSections(EXCLUSIVE_OFFER_GABARIT_SLUG, locale, 'published')
    const filtered = withFallbackExclusiveOfferVault(
      rawSections.filter((section) => {
        const c = resolveCanonicalSectionKey(section.key) ?? section.key
        return ALLOWED_EXCLUSIVE_OFFER_GABARIT_SECTIONS.has(c)
      }),
      locale,
    )

    const rendererContext: SectionPageRendererContext = {}

    return (
      <main className="flex flex-col">
        {filtered.map((section) => {
          const c = resolveCanonicalSectionKey(section.key) ?? section.key
          const isFullBleed = FULL_BLEED_OFFER_GABARIT.has(c)
          const sectionHasOwnMaxWidth = c === 'exclusive_offer_vault'

          if (c === 'exclusive_offer_vault') {
            return (
              <div
                key={section.id}
                className={cn(
                  !isFullBleed &&
                    !sectionHasOwnMaxWidth &&
                    'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8',
                )}
              >
                <GabaritPreviewPlaceholder variant="exclusive_offer" />
              </div>
            )
          }

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
                rendererContext={rendererContext}
              />
            </div>
          )
        })}
      </main>
    )
  }

  notFound()
}
