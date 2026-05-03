import { cache } from 'react'
import type { Metadata } from 'next'
import { notFound, permanentRedirect } from 'next/navigation'

import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { prisma } from '@/lib/prisma'
import {
  EXCLUSIVE_OFFER_GABARIT_TEMPLATE,
  VAULT_BUILDER_TEMPLATE,
} from '@/lib/catalog/packagedCatalogHelpers'
import { buildPublicCmsPageMetadata } from '@/lib/metadata/cmsPageMetadata'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { buildHreflangLanguageUrls, getLocalesQualifiedForHreflang } from '@/lib/cms/cmsPageHreflang'
import { CmsDatabaseUnavailable } from '@/components/cms/CmsDatabaseUnavailable'
import { isDatabaseUnreachable } from '@/lib/prisma/isDatabaseUnreachable'
import type { Locale } from '@/config/locales'
import { isValidLocale } from '@/config/locales'

const getCmsPageBySlug = cache(async (slug: string) =>
  prisma.page.findUnique({ where: { slug } }),
)

type Props = {
  params: { locale: string; slug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale: localeParam, slug } = params
  if (!isValidLocale(localeParam)) {
    notFound()
  }
  const locale = localeParam as Locale

  if (slug === 'home') {
    notFound()
  }

  try {
    const page = await getCmsPageBySlug(slug)
    if (!page) {
      notFound()
    }
    if (page.urlPath === '/') {
      notFound()
    }

    if (page.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
      notFound()
    }

    const canonicalPath =
      page.template === VAULT_BUILDER_TEMPLATE
        ? `/${locale}/projects/${slug}`
        : `/${locale}/${slug}`

    const seo = await resolvePageSeoFields(page.id, locale)

    let hreflangLanguages: Record<string, string> | undefined
    if (page.template !== VAULT_BUILDER_TEMPLATE) {
      const qualified = await getLocalesQualifiedForHreflang(page.id)
      if (qualified.includes(locale)) {
        hreflangLanguages = buildHreflangLanguageUrls(qualified, (l) => `/${l}/${slug}`)
      }
    }

    return buildPublicCmsPageMetadata({
      title: seo.title,
      description: seo.description,
      canonicalPath,
      locale,
      ogTitle: seo.ogTitle,
      ogDescription: seo.ogDescription,
      hreflangLanguages,
    })
  } catch (error) {
    if (isDatabaseUnreachable(error)) {
      return buildPublicCmsPageMetadata({
        title: null,
        description: null,
        canonicalPath: `/${locale}/${slug}`,
        locale,
      })
    }
    throw error
  }
}

export default async function LocalizedCmsPublicPage({ params }: Props) {
  const { locale: localeParam, slug } = params
  if (!isValidLocale(localeParam)) {
    notFound()
  }
  const locale = localeParam as Locale

  if (slug === 'home') {
    notFound()
  }

  try {
    const page = await getCmsPageBySlug(slug)

    if (!page) {
      notFound()
    }

    if (page.urlPath === '/') {
      notFound()
    }

    if (page.template === EXCLUSIVE_OFFER_GABARIT_TEMPLATE) {
      notFound()
    }

    if (page.template === VAULT_BUILDER_TEMPLATE) {
      permanentRedirect(`/${locale}/projects/${slug}`)
    }

    const sections = await getPageSections(slug, locale, 'published')

    if (sections.length === 0) {
      notFound()
    }

    const firstCanonical =
      resolveCanonicalSectionKey(sections[0]!.key) ?? sections[0]!.key
    const blogHeroBleedsFirst =
      firstCanonical === 'blog_hero' || firstCanonical === 'blog_article_hero'

    return (
      <main className="flex flex-col">
        {sections.map((section, index) => (
          <SectionRenderer
            key={section.id}
            section={section}
            locale={locale}
            blogHeroBleedUnderNav={blogHeroBleedsFirst && index === 0}
          />
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
