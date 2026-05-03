import { prisma } from '@/lib/prisma'
import { ContentStatus, type Prisma } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { effectiveIsCompanyNews } from '@/lib/blog/articleService'
import { resolveArticleCategoryLabels } from '@/lib/blog/articleCategoryLabels'
import {
  resolveArticleBlocksForPublic,
  type NormalizedArticleBlock,
} from '@/lib/blog/normalizeArticleBlocks'
import {
  parseArticleGalleryMediaIds,
  resolveGalleryUrlsForMediaIds,
  resolveArticleDocumentsWithUrls,
} from '@/lib/blog/articleAttachments'

export type PublicArticleBlock = NormalizedArticleBlock

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
 * Article publié + médias résolus (cover, galerie, blocs) pour le site.
 */
export async function getPublicArticle(slug: string, locale: string) {
  const article = await prisma.article.findUnique({
    where: { slug },
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

  let projects: ArticleProjectWithProject[] = []
  if (article) {
    const articleProjects = await prisma.articleProject.findMany({
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
    projects = articleProjects
  }

  let categories: Array<{ id: string; slug: string; label: string }> = []
  const categorySlugs: string[] = (() => {
    if (!article) return []
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

  if (article && categorySlugs.length > 0) {
    categories = await resolveArticleCategoryLabels(categorySlugs, locale)
  }

  if (!article || article.status !== ContentStatus.PUBLISHED) {
    return null
  }

  const i18n = article.i18n[0]
  if (!i18n) {
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

  const galleryMediaIds = parseArticleGalleryMediaIds((article as { galleryMediaIds?: unknown }).galleryMediaIds)
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
    projects,
    categories,
    locale,
    articleType: article.articleType,
    isCompanyNews: isCompanyNewsFlag,
  }
}

export type PublicArticle = NonNullable<Awaited<ReturnType<typeof getPublicArticle>>>
