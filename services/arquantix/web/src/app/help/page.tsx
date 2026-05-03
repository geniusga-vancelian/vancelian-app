import { getHelpCollections } from '@/lib/help/get-help-data'
import { SectionHelpHero } from '@/components/sections/SectionHelpHero'
import { SectionHelpCollectionsGrid } from '@/components/sections/SectionHelpCollectionsGrid'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { prisma } from '@/lib/prisma'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { shouldUseHeroSecondaryImageOverlay } from '@/lib/cms/heroSecondaryNav'
import { cn } from '@/lib/utils'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import type { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams: {} })
  return {
    title: siteCommonCta(locale, 'help_meta_title'),
    description: siteCommonCta(locale, 'help_meta_description'),
  }
}

export default async function HelpPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>
}) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams })

  // Check if a CMS page with slug "help" exists
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'help' },
  })

  // If CMS page exists, render via CMS sections
  if (cmsPage) {
    const sections = await getPageSections('help', locale, 'published')
    const overlayHero = shouldUseHeroSecondaryImageOverlay(sections)

    if (sections.length > 0) {
      return (
        <div
          className={cn(
            'min-h-screen bg-white',
            !overlayHero && 'pt-20 md:pt-24',
          )}
        >
          {sections.map((section) => (
            <SectionRenderer
              key={section.id}
              section={section}
              locale={locale}
              collectionSlug={undefined}
              categorySlug={undefined}
            />
          ))}
        </div>
      )
    }
  }

  // Fallback i18n : rendu sans CMS, libellés tirés de siteCommonCta(locale, ...).
  // Toute édition durable doit passer par le CMS (Page "help" + sections).
  return (
    <div className="min-h-screen bg-white pt-20 md:pt-24">
        <SectionHelpHero
          title={siteCommonCta(locale, 'help_fallback_hero_title')}
          placeholderSearch={siteCommonCta(locale, 'help_fallback_hero_search_placeholder')}
          backgroundStyle="purple"
          locale={locale}
        />
        <SectionHelpCollectionsGrid
          sectionTitle={siteCommonCta(locale, 'help_fallback_collections_title')}
          sectionSubtitle={siteCommonCta(locale, 'help_fallback_collections_subtitle')}
          cardCtaLabel={siteCommonCta(locale, 'help_fallback_collections_cta')}
          articlesCountLabel={siteCommonCta(locale, 'help_fallback_articles_count')}
          emptyTitle={siteCommonCta(locale, 'help_fallback_empty_title')}
          emptySubtitle={siteCommonCta(locale, 'help_fallback_empty_subtitle')}
          locale={locale}
        />
    </div>
  )
}

