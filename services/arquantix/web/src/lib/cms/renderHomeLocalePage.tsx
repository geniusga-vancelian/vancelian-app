import { notFound } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'
import { getHomeCmsPage } from '@/lib/cms/homeCmsPage'
import { isDatabaseUnreachable } from '@/lib/prisma/isDatabaseUnreachable'
import { CmsDatabaseUnavailable } from '@/components/cms/CmsDatabaseUnavailable'
import type { Locale } from '@/config/locales'

/**
 * Home CMS sous `/{locale}` (phase 2A). La locale vient du segment d’URL uniquement.
 */
export async function HomeLocalePublicPage({ locale }: { locale: Locale }) {
  try {
    const homeCmsSlug = await resolveHomePageCmsSlug()
    const page = await getHomeCmsPage()

    if (!page) {
      notFound()
    }

    if (homeCmsSlug === 'home' && page.urlPath !== '/') {
      notFound()
    }

    let sections = await getPageSections(homeCmsSlug, locale, 'published')
    if (sections.length === 0 || sections.every((s) => !s.data || Object.keys(s.data).length === 0)) {
      sections = await getPageSections(homeCmsSlug, locale, 'draft')
    }

    if (sections.length === 0) {
      notFound()
    }

    return (
      <main className="flex flex-col">
        {sections.map((section) => (
          <SectionRenderer key={section.id} section={section} />
        ))}
      </main>
    )
  } catch (error) {
    if (isDatabaseUnreachable(error)) {
      return <CmsDatabaseUnavailable />
    }
    throw error
  }
}
