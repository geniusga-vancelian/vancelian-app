import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getHomeCmsPage } from '@/lib/cms/homeCmsPage'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import { buildHreflangLanguageUrls, getLocalesQualifiedForHreflang } from '@/lib/cms/cmsPageHreflang'
import { HomeLocalePublicPage } from '@/lib/cms/renderHomeLocalePage'
import { buildPublicCmsPageMetadata } from '@/lib/metadata/cmsPageMetadata'
import { isDatabaseUnreachable } from '@/lib/prisma/isDatabaseUnreachable'
import { isValidLocale, type Locale } from '@/config/locales'

export const dynamic = 'force-dynamic'

type Props = {
  params: { locale: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = params.locale
  if (!isValidLocale(locale)) {
    notFound()
  }
  const loc = locale as Locale

  const fallbackMeta = () =>
    buildPublicCmsPageMetadata({
      title: null,
      description: null,
      canonicalPath: `/${loc}`,
      locale: loc,
    })

  try {
    const page = await getHomeCmsPage()
    if (!page) {
      return fallbackMeta()
    }

    const homeCmsSlug = await resolveHomePageCmsSlug()
    if (homeCmsSlug === 'home' && page.urlPath !== '/') {
      return fallbackMeta()
    }

    const seo = await resolvePageSeoFields(page.id, loc)

    let hreflangLanguages: Record<string, string> | undefined
    const qualified = await getLocalesQualifiedForHreflang(page.id)
    if (qualified.includes(loc)) {
      hreflangLanguages = buildHreflangLanguageUrls(qualified, (l) => `/${l}`)
    }

    return buildPublicCmsPageMetadata({
      title: seo.title,
      description: seo.description,
      canonicalPath: `/${loc}`,
      locale: loc,
      ogTitle: seo.ogTitle,
      ogDescription: seo.ogDescription,
      hreflangLanguages,
    })
  } catch (error) {
    if (isDatabaseUnreachable(error)) {
      return fallbackMeta()
    }
    throw error
  }
}

export default async function LocalizedHomePage({ params }: Props) {
  const locale = params.locale
  if (!isValidLocale(locale)) {
    notFound()
  }
  return <HomeLocalePublicPage locale={locale as Locale} />
}
