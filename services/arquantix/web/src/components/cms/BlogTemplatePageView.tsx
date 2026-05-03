import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { shouldUseHeroSecondaryImageOverlay } from '@/lib/cms/heroSecondaryNav'
import {
  BLOG_LIST_TEMPLATE_FULL_BLEED_CANONICAL_KEYS,
  BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS,
  blogListTemplateFirstSectionBleedsUnderNav,
} from '@/lib/cms/blogListTemplateSectionPolicy'
import { cn } from '@/lib/utils'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'

const BLOG_PAGE_SLUG = 'blog'

type ContentResolutionMode = 'published' | 'draft'

/**
 * Rendu liste blog piloté par le CMS (gabarit `blog`) — partagé entre la page publique
 * et l’aperçu admin `/preview/blog` pour éviter les écarts (mosaïque, pagination, enveloppe).
 */
export async function BlogTemplatePageView({
  locale,
  category,
  pageNum,
  mosaicPageNum,
  segment,
  contentStatus,
}: {
  locale: string
  category?: string
  pageNum: number
  mosaicPageNum: number
  segment?: string
  contentStatus: ContentResolutionMode
}) {
  const sections = await getPageSections(BLOG_PAGE_SLUG, locale, contentStatus)
  const blogSections = sections.filter((section) => {
    const canonical = resolveCanonicalSectionKey(section.key) ?? section.key
    return BLOG_LIST_TEMPLATE_RENDER_CANONICAL_KEYS.has(canonical)
  })

  const overlayHero = shouldUseHeroSecondaryImageOverlay(blogSections)
  const firstCanonical =
    blogSections.length > 0
      ? resolveCanonicalSectionKey(blogSections[0].key) ?? blogSections[0].key
      : null
  const blogHeroBleedsUnderNav = blogListTemplateFirstSectionBleedsUnderNav(firstCanonical)

  if (blogSections.length === 0) {
    return (
      <div className="min-h-screen bg-white pt-20 md:pt-24">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="py-12 text-center">
            <p className="text-gray-500">{siteCommonCta(locale, 'blog_fallback_unconfigured')}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'min-h-screen bg-white',
        !overlayHero && !blogHeroBleedsUnderNav && 'pt-20 md:pt-24',
      )}
    >
      <div className={cn(!blogHeroBleedsUnderNav && 'pt-12')}>
        {blogSections.map((section, index) => {
          const canonical = resolveCanonicalSectionKey(section.key) ?? section.key
          const isFullBleed = BLOG_LIST_TEMPLATE_FULL_BLEED_CANONICAL_KEYS.has(canonical)

          return (
            <div
              key={section.id}
              className={cn(!isFullBleed && 'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8')}
            >
              <SectionRenderer
                section={section}
                locale={locale}
                category={category}
                page={pageNum}
                mosaicPage={mosaicPageNum}
                blogSegment={segment}
                blogHeroBleedUnderNav={
                  blogHeroBleedsUnderNav &&
                  index === 0 &&
                  (canonical === 'blog_hero' || canonical === 'blog_article_hero')
                }
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
