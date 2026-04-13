/**
 * Service layer for blog articles.
 * Centralizes article fetching, pagination, and filtering logic.
 */

import { prisma } from '@/lib/prisma'
import { ContentStatus, ArticleBlockType, type Prisma } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { resolveArticleCategoryLabels } from '@/lib/blog/articleCategoryLabels'

export interface ArticlePreview {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  authorName: string
  authorRole: string | null
  publishedAt: string | null
  readingTime: number
  categorySlugs: string[] | null
  isMilestone: boolean
  articleType: 'NEWS' | 'ANALYSIS'
  /** True pour actualités entreprise (NEWS uniquement ; dérivé du champ DB + legacy slug `vancelian`). */
  isCompanyNews: boolean
}

export type BlogFeedSegment = 'market' | 'company' | 'analysis'

export interface BlogFeedParams {
  locale: string
  category?: string
  articleType?: 'NEWS' | 'ANALYSIS'
  /** Filtre UX : market = défaut (exclut company du flux principal), company = uniquement company news, analysis = ANALYSIS. */
  segment?: BlogFeedSegment
  page: number
  pageSize: number
}

export interface ArticlesByProjectParams {
  projectId: string
  locale: string
  limit?: number
}

export interface BlogFeedResult {
  featured: ArticlePreview | null
  highlighted: ArticlePreview[]
  /** Actualités entreprise — bandeau dédié (segment market uniquement). */
  companyNews: ArticlePreview[]
  articles: ArticlePreview[]
  pagination: {
    page: number
    pageSize: number
    total: number
    hasMore: boolean
  }
}

/** Slug catégorie legacy pour company news (fallback tant que la migration slug n’est pas partout). */
export const VANCELIAN_COMPANY_CATEGORY_SLUG = 'vancelian'

/** Aligné sur `calculateReadingTime` (Prisma `ArticleBlock` / types de blocs). */
export type ArticleBlocksReadingTimeFn = (
  blocks: Array<{ type: string; data: unknown }>
) => number

const ARTICLE_INCLUDE = {
  coverMedia: true,
  blocks: {
    orderBy: { order: 'asc' as const },
    take: 20,
  },
} satisfies Prisma.ArticleInclude

/**
 * Parse categorySlugs from Article (handles JSON string or array)
 */
export function parseCategorySlugs(categorySlugs: unknown): string[] {
  if (!categorySlugs) return []
  if (Array.isArray(categorySlugs)) return categorySlugs.filter((x): x is string => typeof x === 'string' && x.length > 0)
  if (typeof categorySlugs === 'string') {
    try {
      const parsed = JSON.parse(categorySlugs)
      return Array.isArray(parsed) ? parsed.filter((x: unknown): x is string => typeof x === 'string' && x.length > 0) : []
    } catch {
      return []
    }
  }
  return []
}

/**
 * Company news effectif : champ DB + legacy slug `vancelian` (NEWS uniquement).
 */
export function effectiveIsCompanyNews(article: {
  articleType: string
  isCompanyNews?: boolean | null
  categorySlugs: unknown
}): boolean {
  const t = (article.articleType || 'NEWS').toUpperCase()
  if (t === 'ANALYSIS' || t === 'RESEARCH') return false
  if (article.isCompanyNews === true) return true
  return parseCategorySlugs(article.categorySlugs).includes(VANCELIAN_COMPANY_CATEGORY_SLUG)
}

/**
 * IDs des articles « company news » publiés (NEWS + isCompanyNews ou legacy vancelian).
 */
export async function getCompanyNewsArticleIds(): Promise<string[]> {
  const rows = await prisma.$queryRaw<{ id: string }[]>`
    SELECT id FROM articles
    WHERE status = 'PUBLISHED'
      AND article_type = 'NEWS'
      AND (
        is_company_news = true
        OR category_slugs::jsonb @> '["vancelian"]'::jsonb
      )
  `
  return rows.map((r) => r.id)
}

/**
 * Get article IDs that match a category (PostgreSQL JSONB @> operator)
 */
async function getArticleIdsByCategory(category: string): Promise<string[]> {
  const rows = await prisma.$queryRaw<{ id: string }[]>`
    SELECT id FROM articles
    WHERE status = 'PUBLISHED'
      AND category_slugs::jsonb @> ${JSON.stringify([category])}::jsonb
  `
  return rows.map((r) => r.id)
}

/**
 * Build Prisma where clause for articles
 */
function buildFeedWhereClause(params: {
  allowedIds?: string[] | null
  excludeIds?: string[]
  articleType?: 'NEWS' | 'ANALYSIS'
}): Prisma.ArticleWhereInput {
  const where: Prisma.ArticleWhereInput = {
    status: ContentStatus.PUBLISHED,
  }
  if (params.articleType) where.articleType = params.articleType

  const excludeIds = params.excludeIds ?? []

  if (params.allowedIds !== undefined) {
    if (params.allowedIds === null || params.allowedIds.length === 0) {
      return { ...where, id: { in: [] } }
    }
    const ids = excludeIds.length > 0
      ? params.allowedIds.filter((id) => !excludeIds.includes(id))
      : params.allowedIds
    if (ids.length === 0) {
      return { ...where, id: { in: [] } }
    }
    where.id = { in: ids }
  } else if (excludeIds.length > 0) {
    where.id = { notIn: excludeIds }
  }

  return where
}

/**
 * Transform raw article to ArticlePreview with presigned URLs
 */
async function toArticlePreview(
  article: {
    id: string
    slug: string
    authorName: string
    authorRole: string | null
    publishedAt: Date | null
    categorySlugs: unknown
    isMilestone: boolean
    articleType: string
    isCompanyNews?: boolean | null
    coverMedia: { url: string; key: string | null } | null
    blocks: Array<{ type: string; data: unknown }>
    i18n: Array<{ title: string; standfirst: string }>
  },
  calculateReadingTime: ArticleBlocksReadingTimeFn
): Promise<ArticlePreview | null> {
  const i18n = article.i18n[0]
  if (!i18n) return null

  let coverUrl = article.coverMedia?.url || ''
  if (article.coverMedia?.key) {
    try {
      coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
    } catch {
      // Fallback to original URL
    }
  }

  const readingTime = calculateReadingTime(article.blocks)

  return {
    id: article.id,
    slug: article.slug,
    title: i18n.title,
    standfirst: i18n.standfirst,
    coverUrl,
    authorName: article.authorName,
    authorRole: article.authorRole,
    publishedAt: article.publishedAt?.toISOString() ?? null,
    readingTime,
    categorySlugs: parseCategorySlugs(article.categorySlugs),
    isMilestone: article.isMilestone,
    articleType: article.articleType === 'ANALYSIS' ? 'ANALYSIS' : 'NEWS',
    isCompanyNews: effectiveIsCompanyNews({
      articleType: article.articleType,
      isCompanyNews: article.isCompanyNews,
      categorySlugs: article.categorySlugs,
    }),
  }
}

/**
 * Fetch blog feed with proper database-side pagination
 */
export async function getBlogFeed(
  params: BlogFeedParams,
  calculateReadingTime: ArticleBlocksReadingTimeFn
): Promise<BlogFeedResult> {
  const started = Date.now()
  const { locale, category, articleType, page, pageSize, segment: segmentParam } = params
  const segment: BlogFeedSegment = segmentParam ?? 'market'

  try {
    return await loadBlogFeedInner(
      { ...params, segment },
      calculateReadingTime,
      started
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    const stack = err instanceof Error ? err.stack : undefined
    console.error('[blog] getBlogFeed: prisma query failed', {
      ms: Date.now() - started,
      locale,
      category,
      articleType,
      segment,
      page,
      pageSize,
      message,
      stack,
    })
    throw err
  }
}

async function loadBlogFeedInner(
  params: BlogFeedParams & { segment: BlogFeedSegment },
  calculateReadingTime: ArticleBlocksReadingTimeFn,
  started: number
): Promise<BlogFeedResult> {
  const { locale, category, page, pageSize, segment } = params
  let { articleType } = params

  if (segment === 'analysis') {
    articleType = 'ANALYSIS'
  }
  if (segment === 'company') {
    articleType = 'NEWS'
  }

  const i18nWhere = { locale }
  const baseInclude = {
    ...ARTICLE_INCLUDE,
    i18n: { where: i18nWhere, take: 1 },
  }

  const companyArticleIds = await getCompanyNewsArticleIds()

  // Resolve category filter: when category provided, get matching article IDs via raw SQL.
  // Legacy slug `vancelian` = même périmètre que les company news (champ + fallback slug).
  let categoryIds = category
    ? category === VANCELIAN_COMPANY_CATEGORY_SLUG
      ? await getCompanyNewsArticleIds()
      : await getArticleIdsByCategory(category)
    : undefined

  if (segment === 'company' && categoryIds !== undefined && categoryIds.length > 0) {
    const companySet = new Set(companyArticleIds)
    categoryIds = categoryIds.filter((id) => companySet.has(id))
  }

  const vancelianArticleIds =
    segment === 'market' && !category ? companyArticleIds : []

  // 1. Featured article (page 1 only, no category filter)
  let featured: ArticlePreview | null = null
  let featuredId: string | null = null

  if (page === 1 && !category) {
    const featuredWhere: Prisma.ArticleWhereInput = {
      ...buildFeedWhereClause({
        excludeIds: [],
        articleType,
      }),
      isFeatured: true,
    }
    if (segment === 'company') {
      featuredWhere.id = { in: companyArticleIds }
    }

    const featuredArticle = await prisma.article.findFirst({
      where: featuredWhere,
      include: baseInclude,
      orderBy: { publishedAt: 'desc' },
    })

    const fallbackWhere: Prisma.ArticleWhereInput = buildFeedWhereClause({
      articleType,
    })
    if (segment === 'company') {
      fallbackWhere.id = { in: companyArticleIds }
    }

    const articleToUse =
      featuredArticle ??
      (await prisma.article.findFirst({
        where: fallbackWhere,
        include: baseInclude,
        orderBy: { publishedAt: 'desc' },
      }))

    if (articleToUse) {
      featured = await toArticlePreview(articleToUse, calculateReadingTime)
      featuredId = articleToUse.id
    }
  }

  // 2. Highlighted articles (page 1 only, exclude featured)
  let highlighted: ArticlePreview[] = []
  const excludeIds: string[] = featuredId ? [featuredId] : []

  if (page === 1 && !category) {
    const highlightedWhere: Prisma.ArticleWhereInput = {
      ...buildFeedWhereClause({ excludeIds, articleType }),
      isHighlighted: true,
    }
    if (segment === 'company') {
      highlightedWhere.id = { in: companyArticleIds }
    }

    const highlightedArticles = await prisma.article.findMany({
      where: highlightedWhere,
      include: baseInclude,
      orderBy: { publishedAt: 'desc' },
      take: 5,
    })

    highlighted = (
      await Promise.all(
        highlightedArticles.map((a) => toArticlePreview(a, calculateReadingTime))
      )
    ).filter((a): a is ArticlePreview => a !== null)

    excludeIds.push(...highlighted.map((a) => a.id))
  }

  // Bandeau « Company News » : segment market uniquement (pas de doublon avec vue company-only).
  let companyNews: ArticlePreview[] = []
  if (page === 1 && !category && segment === 'market' && vancelianArticleIds.length > 0) {
    const stripArticles = await prisma.article.findMany({
      where: {
        id: { in: vancelianArticleIds },
        status: ContentStatus.PUBLISHED,
        ...(excludeIds.length > 0 ? { NOT: { id: { in: excludeIds } } } : {}),
      },
      include: baseInclude,
      orderBy: { publishedAt: 'desc' },
      take: 4,
    })
    companyNews = (
      await Promise.all(stripArticles.map((a) => toArticlePreview(a, calculateReadingTime)))
    ).filter((a): a is ArticlePreview => a !== null)
  }

  // 3. Feed articles
  let feedExcludeIds = [...excludeIds]
  if (segment === 'market' && !category) {
    feedExcludeIds = [...feedExcludeIds, ...vancelianArticleIds]
  }

  let allowedForFeed: string[] | null | undefined = categoryIds
  if (segment === 'company') {
    if (categoryIds !== undefined) {
      allowedForFeed = categoryIds
    } else {
      allowedForFeed = companyArticleIds.length > 0 ? companyArticleIds : []
    }
  }

  const feedWhere = buildFeedWhereClause({
    allowedIds: allowedForFeed,
    excludeIds: feedExcludeIds,
    articleType,
  })

  const [feedArticles, totalCount] = await Promise.all([
    prisma.article.findMany({
      where: feedWhere,
      include: baseInclude,
      orderBy: { publishedAt: 'desc' },
      skip: (page - 1) * pageSize,
      take: pageSize + 1,
    }),
    prisma.article.count({ where: feedWhere }),
  ])

  const hasMore = feedArticles.length > pageSize
  const articlesPage = hasMore ? feedArticles.slice(0, pageSize) : feedArticles

  const articles = (
    await Promise.all(
      articlesPage.map((a) => toArticlePreview(a, calculateReadingTime))
    )
  ).filter((a): a is ArticlePreview => a !== null)

  const emptyFeed =
    !featured &&
    highlighted.length === 0 &&
    companyNews.length === 0 &&
    articles.length === 0 &&
    totalCount === 0
  if (emptyFeed) {
    console.warn('[blog] blog feed empty (no published articles for this locale/filters)', {
      ms: Date.now() - started,
      locale,
      category,
      articleType,
      segment,
      page,
    })
  }

  return {
    featured,
    highlighted,
    companyNews,
    articles,
    pagination: {
      page,
      pageSize,
      total: totalCount,
      hasMore,
    },
  }
}

/**
 * Get articles linked to a project via ArticleProject (related project section).
 * Used by the project detail page and mobile app to show "news du projet".
 */
export async function getArticlesByProject(
  params: ArticlesByProjectParams,
  calculateReadingTime: ArticleBlocksReadingTimeFn
): Promise<ArticlePreview[]> {
  const { projectId, locale, limit = 20 } = params

  const articleProjects = await prisma.articleProject.findMany({
    where: { projectId },
    select: { articleId: true },
    orderBy: { createdAt: 'desc' },
    take: limit,
  })

  const articleIds = articleProjects.map((ap) => ap.articleId)
  if (articleIds.length === 0) return []

  const i18nWhere = { locale }
  const articles = await prisma.article.findMany({
    where: {
      id: { in: articleIds },
      status: ContentStatus.PUBLISHED,
    },
    include: {
      ...ARTICLE_INCLUDE,
      i18n: { where: i18nWhere, take: 1 },
    },
    orderBy: { publishedAt: 'desc' },
  })

  const previews = await Promise.all(
    articles.map((a) => toArticlePreview(a, calculateReadingTime))
  )
  return previews.filter((a): a is ArticlePreview => a !== null)
}

// ---------------------------------------------------------------------------
// Article detail (for API / Flutter app)
// ---------------------------------------------------------------------------

export interface ArticleBlockApi {
  id: string
  type: string
  order: number
  data: Record<string, unknown>
  imageUrl?: string
}

export interface ArticleDetailApi {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  coverTitle?: string
  coverCredit?: string
  coverSource?: string
  authorName: string
  authorRole: string | null
  publishedAt: string | null
  updatedAt: string
  readingTime: number
  categorySlugs: string[]
  categories: Array<{ id: string; slug: string; label: string }>
  videoUrl: string | null
  galleryUrls: string[]
  documents: Array<{ mediaId: string; title: string; url: string | null }>
  blocks: ArticleBlockApi[]
  articleType: string
  isCompanyNews: boolean
}

/**
 * Fetch a single published article by slug for API consumption (Flutter, etc.)
 */
export async function getArticleBySlug(
  slug: string,
  locale: string,
  calculateReadingTime: ArticleBlocksReadingTimeFn
): Promise<ArticleDetailApi | null> {
  const article = await prisma.article.findUnique({
    where: { slug },
    include: {
      coverMedia: true,
      i18n: { where: { locale }, take: 1 },
      blocks: {
        orderBy: { order: 'asc' },
        include: { i18n: { where: { locale }, take: 1 } },
      },
    },
  })

  if (!article || article.status !== ContentStatus.PUBLISHED) {
    return null
  }

  const i18n = article.i18n[0]
  if (!i18n) return null

  let coverUrl = article.coverMedia?.url || ''
  if (article.coverMedia?.key) {
    try {
      coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
    } catch {
      // keep original
    }
  }

  const categorySlugs = parseCategorySlugs(article.categorySlugs)
  const categories = await resolveArticleCategoryLabels(categorySlugs, locale)

  const galleryMediaIds: string[] = (() => {
    const raw = (article as { galleryMediaIds?: unknown }).galleryMediaIds
    if (!raw) return []
    if (Array.isArray(raw)) return raw.filter((x): x is string => typeof x === 'string' && x.length > 0)
    if (typeof raw === 'string') {
      try {
        const p = JSON.parse(raw)
        return Array.isArray(p) ? p.filter((x: unknown): x is string => typeof x === 'string' && x.length > 0) : []
      } catch {
        return []
      }
    }
    return []
  })()

  const galleryUrls: string[] = []
  for (const mediaId of galleryMediaIds) {
    try {
      const media = await prisma.media.findUnique({ where: { id: mediaId } })
      if (media) {
        let url = media.url
        if (media.key) {
          try {
            url = await getPresignedUrl(media.key, 3600)
          } catch {
            // keep original
          }
        }
        galleryUrls.push(url)
      }
    } catch {
      // skip
    }
  }

  type DocRef = { mediaId?: string; title?: string }
  const documentsRaw = (Array.isArray(article.documents) ? article.documents : []) as DocRef[]
  const documents = await Promise.all(
    documentsRaw.map(async (doc) => {
      if (!doc?.mediaId) {
        return { mediaId: '', title: doc.title || 'Document', url: null as string | null }
      }
      try {
        const media = await prisma.media.findUnique({ where: { id: doc.mediaId } })
        if (!media) return { mediaId: doc.mediaId, title: doc.title || 'Document', url: null }
        let url = media.url
        if (media.key) {
          try {
            url = await getPresignedUrl(media.key, 3600)
          } catch {
            // keep original
          }
        }
        return { mediaId: doc.mediaId, title: doc.title || 'Document', url }
      } catch {
        return { mediaId: doc.mediaId, title: doc.title || 'Document', url: null }
      }
    })
  )

  const blocks: ArticleBlockApi[] = await Promise.all(
    article.blocks.map(async (block) => {
      const blockData = block.i18n[0]?.data || block.data
      const data = (typeof blockData === 'object' && blockData !== null ? blockData : {}) as Record<string, unknown>

      let imageUrl: string | undefined
      if (block.type === ArticleBlockType.IMAGE && (data.mediaId as string)) {
        try {
          const media = await prisma.media.findUnique({ where: { id: data.mediaId as string } })
          if (media?.key) {
            try {
              imageUrl = await getPresignedUrl(media.key, 3600)
            } catch {
              imageUrl = media.url
            }
          } else if (media?.url) {
            imageUrl = media.url
          }
        } catch {
          // no image
        }
      }

      if (block.type === ArticleBlockType.DOCUMENT && (data.mediaId as string)) {
        try {
          const media = await prisma.media.findUnique({ where: { id: data.mediaId as string } })
          if (media) {
            let url = media.url
            if (media.key) {
              try {
                url = await getPresignedUrl(media.key, 3600)
              } catch {
                // keep original
              }
            }
            data.url = url
          }
        } catch {
          // no url
        }
      }

      return {
        id: block.id,
        type: block.type,
        order: block.order,
        data,
        ...(imageUrl && { imageUrl }),
      }
    })
  )

  const articleType = article.articleType || 'NEWS'
  const isCompanyNews = effectiveIsCompanyNews({
    articleType,
    isCompanyNews: article.isCompanyNews,
    categorySlugs: article.categorySlugs,
  })

  return {
    id: article.id,
    slug: article.slug,
    title: i18n.title,
    standfirst: i18n.standfirst,
    coverUrl,
    coverTitle: (i18n as { coverTitle?: string }).coverTitle ?? (article as { coverTitle?: string }).coverTitle ?? undefined,
    coverCredit: (article as { coverCredit?: string }).coverCredit ?? undefined,
    coverSource: (article as { coverSource?: string }).coverSource ?? undefined,
    authorName: article.authorName,
    authorRole: article.authorRole,
    publishedAt: article.publishedAt?.toISOString() ?? null,
    updatedAt: article.updatedAt.toISOString(),
    readingTime: calculateReadingTime(article.blocks),
    categorySlugs,
    categories,
    videoUrl: article.videoUrl,
    galleryUrls,
    documents,
    blocks,
    articleType,
    isCompanyNews,
  }
}
