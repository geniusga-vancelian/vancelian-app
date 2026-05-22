import { defaultLocale } from '@/config/locales'
import { getPageSections } from '@/lib/cms/content'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'
import { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import type { SectionHeroProps } from '@/components/sections/SectionHero'

export type HomeHeroAuthContent = Omit<
  SectionHeroProps,
  'hideCta' | 'className' | 'style' | 'ctaText' | 'ctaLink' | 'secondaryCtaText' | 'secondaryCtaHref'
>

async function resolveHomeHeroSectionData(): Promise<Record<string, unknown> | undefined> {
  const homeCmsSlug = await resolveHomePageCmsSlug()

  let sections = await getPageSections(homeCmsSlug, defaultLocale, 'published')
  if (
    sections.length === 0 ||
    sections.every((section) => !section.data || Object.keys(section.data).length === 0)
  ) {
    sections = await getPageSections(homeCmsSlug, defaultLocale, 'draft')
  }

  const heroSection = sections.find((section) => {
    const key = resolveCanonicalSectionKey(section.key) ?? section.key
    return key === 'hero'
  })

  return heroSection?.data as Record<string, unknown> | undefined
}

/**
 * Props hero homepage pour l'écran login/signup portail —
 * même mapping CMS que {@link SectionHero} sur la homepage publique.
 */
export async function resolveHomeHeroAuthContent(): Promise<HomeHeroAuthContent | null> {
  const data = await resolveHomeHeroSectionData()
  if (!data) return null

  const props = mapDataToComponentProps('hero', data, defaultLocale) as HomeHeroAuthContent
  return props
}
