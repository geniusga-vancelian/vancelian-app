import { prisma } from '@/lib/prisma'
import type { Prisma } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { effectiveIsCompanyNews } from '@/lib/blog/articleService'
import { resolveArticleCategoryLabels } from '@/lib/blog/articleCategoryLabels'
import { resolveArticleBlocksForPublic } from '@/lib/blog/normalizeArticleBlocks'
import {
  parseArticleGalleryMediaIds,
  resolveGalleryUrlsForMediaIds,
  resolveArticleDocumentsWithUrls,
} from '@/lib/blog/articleAttachments'
import type { PublicArticle } from '@/lib/blog/getPublicArticle'

type ArticleProjectWithProject = Prisma.ArticleProjectGetPayload<{
  include: {
    project: {
      include: {
        i18n: true
      }
    }
  }
}>

/**
 * Variante admin de {@link getPublicArticle} :
 * - sélection par `id` (pas par `slug`),
 * - aucun filtre `status === PUBLISHED` (le brouillon est rendu tel quel),
 * - même shape de retour pour rester compatible avec `<SectionRenderer blogArticle={...} />`.
 *
 * Réservé aux routes `/preview/*` protégées par auth admin.
 */
export async function getArticleForAdminPreview(
  id: string,
  locale: string,
): Promise<PublicArticle | null> {
  const article = await prisma.article.findUnique({
    where: { id },
    include: {
      coverMedia: true,
      i18n: {
        where: { locale },
      },
      blocks: {
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale },
            take: 1,
          },
        },
      },
    },
  })

  if (!article) {
    return null
  }

  const articleProjects: ArticleProjectWithProject[] = await prisma.articleProject.findMany({
    where: { articleId: article.id },
    include: {
      project: {
        include: {
          i18n: {
            where: { locale },
            take: 1,
          },
        },
      },
    },
    orderBy: { createdAt: 'asc' },
  })

  let categories: Array<{ id: string; slug: string; label: string }> = []
  const categorySlugs: string[] = (() => {
    const raw = (article as { categorySlugs?: unknown }).categorySlugs
    if (!raw) return []
    if (Array.isArray(raw)) return raw.filter(Boolean)
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed.filter(Boolean) : []
      } catch {
        return []
      }
    }
    return []
  })()

  if (categorySlugs.length > 0) {
    categories = await resolveArticleCategoryLabels(categorySlugs, locale)
  }

  const i18n = article.i18n[0]
  if (!i18n) {
    // Cohérent avec getPublicArticle : la route appelle notFound() en l'absence d'i18n.
    return null
  }

  let coverUrl: string | null = null
  if (article.coverMedia) {
    coverUrl = article.coverMedia.url
    if (article.coverMedia.key) {
      try {
        coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
      } catch {
        coverUrl = article.coverMedia.url
      }
    }
  }

  const galleryMediaIds = parseArticleGalleryMediaIds(
    (article as { galleryMediaIds?: unknown }).galleryMediaIds,
  )
  const galleryUrls =
    galleryMediaIds.length > 0 ? await resolveGalleryUrlsForMediaIds(prisma, galleryMediaIds) : []

  const documentsWithUrls = await resolveArticleDocumentsWithUrls(prisma, article.documents)

  const blocksWithUrls = await resolveArticleBlocksForPublic(prisma, article.blocks)

  const isCompanyNewsFlag = effectiveIsCompanyNews({
    articleType: article.articleType,
    isCompanyNews: (article as { isCompanyNews?: boolean | null }).isCompanyNews,
    categorySlugs: article.categorySlugs,
  })

  return {
    ...article,
    i18n,
    coverUrl: coverUrl || '',
    galleryUrls,
    documents: documentsWithUrls,
    blocks: blocksWithUrls,
    projects: articleProjects,
    categories,
    locale,
    articleType: article.articleType,
    isCompanyNews: isCompanyNewsFlag,
  } as PublicArticle
}
