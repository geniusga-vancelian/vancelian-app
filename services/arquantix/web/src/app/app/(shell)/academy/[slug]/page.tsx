import { cookies } from 'next/headers'
import { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { PortalArticleScreen } from '@/components/portal/academy/PortalArticleScreen'
import { getPortalArticleBySlug } from '@/lib/portal/getPortalArticle'
import { portalArticlePublicUrl } from '@/lib/portal/portalArticleRouting'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'

type Props = {
  params: { slug: string }
}

function resolveTitle(view: NonNullable<Awaited<ReturnType<typeof getPortalArticleBySlug>>>) {
  if (view.kind === 'editorial') {
    return view.article.i18n.metaTitle || view.article.i18n.title
  }
  return view.title
}

function resolveDescription(
  view: NonNullable<Awaited<ReturnType<typeof getPortalArticleBySlug>>>,
) {
  if (view.kind === 'editorial') {
    return view.article.i18n.metaDescription || view.article.i18n.standfirst || undefined
  }
  return view.standfirst || undefined
}

function resolveCover(
  view: NonNullable<Awaited<ReturnType<typeof getPortalArticleBySlug>>>,
) {
  if (view.kind === 'editorial') return view.article.coverUrl || undefined
  return view.coverUrl || undefined
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore })
  const view = await getPortalArticleBySlug(params.slug, locale)
  if (!view) return { title: 'Article not found' }

  const title = resolveTitle(view)
  const description = resolveDescription(view)
  const coverUrl = resolveCover(view)
  const canonical = portalArticlePublicUrl(params.slug)

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: coverUrl ? [{ url: coverUrl }] : [],
      type: 'article',
      url: canonical,
    },
  }
}

export default async function PortalAcademyArticlePage({ params }: Props) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore })
  const view = await getPortalArticleBySlug(params.slug, locale)

  if (!view) {
    notFound()
  }

  return <PortalArticleScreen view={view} />
}
