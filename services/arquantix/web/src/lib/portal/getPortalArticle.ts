import { getLocaleOrDefault } from '@/config/locales'
import { getAcademyArticleByGlobalSlug } from '@/lib/academy/get-academy-data'
import { getPublicArticle } from '@/lib/blog/getPublicArticle'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import type { PortalArticleView } from '@/lib/portal/portalArticleTypes'

export type {
  PortalAcademyArticleView,
  PortalEditorialArticleView,
  PortalArticleView,
} from '@/lib/portal/portalArticleTypes'

export { portalArticleTypeLabel } from '@/lib/portal/portalArticleTypes'

export async function getPortalArticleBySlug(
  slug: string,
  locale?: string,
): Promise<PortalArticleView | null> {
  const loc = getLocaleOrDefault(locale)
  const normalizedSlug = slug.trim()
  if (!normalizedSlug) return null

  const editorial = await getPublicArticle(normalizedSlug, loc)
  if (editorial) {
    return { kind: 'editorial', article: editorial }
  }

  const academy = await getAcademyArticleByGlobalSlug(normalizedSlug, loc)
  if (!academy) return null

  const coverUrl = academy.coverMedia
    ? (await resolveArticleCoverUrlForPublic(academy.coverMedia)) ?? ''
    : ''

  return {
    kind: 'academy',
    slug: academy.slug,
    title: academy.title,
    standfirst: academy.standfirst,
    authorName: academy.authorName,
    publishedAt: academy.publishedAt,
    createdAt: academy.updatedAt,
    updatedAt: academy.updatedAt,
    coverUrl,
    blocks: academy.blocks,
    documents: [],
    articleType: 'ACADEMY',
    collectionTitle: academy.collection.title,
    categoryTitle: academy.category.title,
    locale: academy.locale,
  }
}
