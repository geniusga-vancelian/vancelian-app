import { ContentStatus } from '@prisma/client'

import { calculateReadingTime } from '@/lib/blog/readingTime'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { prisma } from '@/lib/prisma'
import { academyCategoryTone } from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'
import { resolvePortalArticleHref } from '@/lib/portal/portalArticleRouting'

/**
 * Articles `articleType=ACADEMY` publiés pour la grille hub portail Académie.
 */
export async function listPortalAcademyTypeArticles(
  locale: string,
  options?: { origin?: string; limit?: number },
): Promise<PortalAcademyArticle[]> {
  const limit = Math.min(Math.max(options?.limit ?? 48, 1), 100)
  const origin = options?.origin

  const articles = await prisma.article.findMany({
    where: {
      articleType: 'ACADEMY',
      status: ContentStatus.PUBLISHED,
    },
    include: {
      coverMedia: true,
      blocks: { orderBy: { order: 'asc' }, take: 20 },
      i18n: { where: { locale }, take: 1 },
      academyCategory: {
        include: {
          i18n: { where: { locale }, take: 1 },
        },
      },
    },
    orderBy: { publishedAt: 'desc' },
    take: limit,
  })

  const out: PortalAcademyArticle[] = []

  for (const article of articles) {
    const i18n = article.i18n[0]
    if (!i18n?.title?.trim()) continue

    const slug = (article.academySlug ?? article.slug).trim()
    if (!slug) continue

    let coverUrl = article.coverMedia?.url ?? ''
    if (article.coverMedia?.key) {
      try {
        coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
      } catch {
        // fallback URL
      }
    }

    const categorySlug = article.academyCategory?.slug ?? null
    const categoryLabel =
      article.academyCategory?.i18n[0]?.title?.trim() ||
      (categorySlug ? categorySlug : 'Academy')

    const path = resolvePortalArticleHref(slug, origin)
    const href =
      origin && !path.startsWith('http') ? `${origin.replace(/\/$/, '')}${path}` : path

    out.push({
      id: article.id,
      slug,
      title: i18n.title.trim(),
      standfirst: (i18n.standfirst ?? '').trim(),
      coverUrl,
      authorName: article.authorName?.trim() || 'Vancelian',
      publishedAt: article.publishedAt?.toISOString() ?? null,
      readingTime: calculateReadingTime(article.blocks ?? []),
      href,
      categorySlug,
      categoryLabel,
      categoryTone: academyCategoryTone(categorySlug),
      articleType: 'ACADEMY',
      isCompanyNews: false,
    })
  }

  return out
}
