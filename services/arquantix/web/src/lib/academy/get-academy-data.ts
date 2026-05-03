import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { resolveArticleBlocksForPublic } from '@/lib/blog/normalizeArticleBlocks'
import { deriveGroupingTags, tagSlugToDisplayTitle } from '@/lib/articles/collectionTags'

/**
 * Tag normalisé tel qu'attendu par les consommateurs publics (web + mobile).
 * Aligné sur `HelpTargetTagDTO` (même format `target_tags`) — on garde les
 * mêmes types de cibles pour permettre un partage UI / pickers entre Help et
 * Academy.
 */
export interface AcademyTargetTagDTO {
  type: 'THEMATIC_CATEGORY' | 'INVESTMENT_TYPE' | 'EXCLUSIVE_OFFER'
  id: string
  slug: string
  label: string
}

const VALID_TARGET_TAG_TYPES = new Set<AcademyTargetTagDTO['type']>([
  'THEMATIC_CATEGORY',
  'INVESTMENT_TYPE',
  'EXCLUSIVE_OFFER',
])

/**
 * Parse les `target_tags` stockés en JSON (tableau d'objets `{type,id,slug,label}`)
 * en filtrant les entrées invalides. Tolère un input string (ré-encodé JSON)
 * comme un input array.
 */
export function normalizeAcademyTargetTags(raw: unknown): AcademyTargetTagDTO[] {
  let source: unknown = raw
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return []
    }
  }
  if (!Array.isArray(source)) return []
  return source
    .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    .filter((row) =>
      typeof row.type === 'string' &&
      VALID_TARGET_TAG_TYPES.has(row.type as AcademyTargetTagDTO['type']) &&
      typeof row.id === 'string' &&
      typeof row.slug === 'string' &&
      typeof row.label === 'string',
    )
    .map((row) => ({
      type: row.type as AcademyTargetTagDTO['type'],
      id: String(row.id),
      slug: String(row.slug),
      label: String(row.label),
    }))
}

async function countAcademyArticlesByCollectionId(collectionId: string): Promise<number> {
  return prisma.article.count({
    where: {
      articleType: 'ACADEMY',
      status: 'PUBLISHED',
      academyCollectionId: collectionId,
    },
  })
}

async function aggregateAcademyArticlePreviewsByCollectionId(
  collectionId: string,
  locale: string,
): Promise<AcademyArticlePreview[]> {
  const articles = await prisma.article.findMany({
    where: {
      articleType: 'ACADEMY',
      status: 'PUBLISHED',
      academyCollectionId: collectionId,
    },
    include: {
      i18n: { where: { locale }, take: 1 },
      academyCategory: { select: { slug: true } },
    },
    orderBy: { publishedAt: 'desc' },
  })

  const previews: AcademyArticlePreview[] = []
  for (const a of articles) {
    const i18n = a.i18n[0]
    if (!i18n) continue
    previews.push({
      id: a.id,
      slug: a.academySlug ?? a.slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      targetTags: normalizeAcademyTargetTags(a.targetTags),
      collectionTags: deriveGroupingTags(a.collectionTags, a.academyCategory?.slug ?? null),
    })
  }
  return previews
}

async function aggregateAcademyArticlePreviewsByCategoryId(
  categoryId: string,
  locale: string,
): Promise<AcademyArticlePreview[]> {
  const cat = await prisma.academyCategory.findUnique({
    where: { id: categoryId },
    select: { collectionId: true, slug: true },
  })
  if (!cat) return []
  const all = await aggregateAcademyArticlePreviewsByCollectionId(cat.collectionId, locale)
  return all.filter((p) => p.collectionTags.includes(cat.slug))
}

/**
 * Comptage Academy pour une catégorie : articles dont les tags de regroupement
 * incluent le slug de cette catégorie (ou rattachement legacy cohérent).
 */
async function countAcademyArticlesByCategoryId(categoryId: string): Promise<number> {
  const cat = await prisma.academyCategory.findUnique({
    where: { id: categoryId },
    select: { slug: true, collectionId: true },
  })
  if (!cat) return 0

  const rows = await prisma.article.findMany({
    where: {
      articleType: 'ACADEMY',
      status: 'PUBLISHED',
      academyCollectionId: cat.collectionId,
    },
    select: {
      collectionTags: true,
      academyCategory: { select: { slug: true } },
    },
  })

  let count = 0
  for (const row of rows) {
    const tags = deriveGroupingTags(row.collectionTags, row.academyCategory?.slug ?? null)
    if (tags.includes(cat.slug)) count++
  }
  return count
}

export interface AcademyCollectionWithCount {
  id: string
  slug: string
  order: number
  title: string
  subtitle: string | null
  description: string | null
  iconKey: string | null
  colorHex: string | null
  articleCount: number
}

export interface AcademyCategoryWithCount {
  id: string
  slug: string
  order: number
  title: string
  description: string | null
  articleCount: number
}

export interface AcademyArticlePreview {
  id: string
  slug: string
  title: string
  standfirst: string | null
  updatedAt: Date
  publishedAt: Date | null
  targetTags: AcademyTargetTagDTO[]
  collectionTags: string[]
}

/**
 * Liste les collections Academy publiées avec comptage total d'articles publiés (collection à plat).
 */
export async function getAcademyCollections(locale?: string): Promise<AcademyCollectionWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collections = await prisma.academyCollection.findMany({
    where: { isPublished: true },
    orderBy: { order: 'asc' },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
    },
  })

  const results = await Promise.all(
    collections.map(async (collection): Promise<AcademyCollectionWithCount | null> => {
      const i18n = collection.i18n[0]
      if (!i18n) return null

      const articleCount = await countAcademyArticlesByCollectionId(collection.id)

      return {
        id: collection.id,
        slug: collection.slug,
        order: collection.order,
        title: i18n.title,
        subtitle: i18n.subtitle ?? null,
        description: i18n.description ?? null,
        iconKey: collection.iconKey ?? null,
        colorHex: collection.colorHex ?? null,
        articleCount,
      }
    }),
  )
  return results.filter((c): c is AcademyCollectionWithCount => c !== null)
}

/**
 * Récupère une collection Academy par slug + comptage total d'articles publiés.
 */
export async function getAcademyCollection(
  slug: string,
  locale?: string,
): Promise<AcademyCollectionWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.academyCollection.findUnique({
    where: { slug },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
    },
  })

  if (!collection || !collection.isPublished) return null
  const i18n = collection.i18n[0]
  if (!i18n) return null

  const articleCount = await countAcademyArticlesByCollectionId(collection.id)

  return {
    id: collection.id,
    slug: collection.slug,
    order: collection.order,
    title: i18n.title,
    subtitle: i18n.subtitle ?? null,
    description: i18n.description ?? null,
    iconKey: collection.iconKey ?? null,
    colorHex: collection.colorHex ?? null,
    articleCount,
  }
}

/**
 * Liste les catégories publiées d'une collection Academy.
 */
export async function getAcademyCategories(
  collectionSlug: string,
  locale?: string,
): Promise<AcademyCategoryWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.academyCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      categories: {
        where: { isPublished: true },
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
        },
      },
    },
  })

  if (!collection) return []

  const cats = await Promise.all(
    collection.categories.map(async (category) => {
      const i18n = category.i18n[0]
      if (!i18n) return null
      const articleCount = await countAcademyArticlesByCategoryId(category.id)
      return {
        id: category.id,
        slug: category.slug,
        order: category.order,
        title: i18n.title,
        description: i18n.description ?? null,
        articleCount,
      }
    }),
  )
  return cats.filter((c): c is AcademyCategoryWithCount => c !== null)
}

/**
 * Modèle Prisma complet collection + catégories (i18n) pour grilles SEO.
 */
export async function getAcademyCollectionWithCategories(
  collectionSlug: string,
  locale?: string,
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.academyCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
      categories: {
        where: { isPublished: true },
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
        },
      },
    },
  })

  if (!collection || !collection.isPublished) return null
  return collection
}

/**
 * Récupère une catégorie Academy par slugs collection/catégorie + comptage.
 */
export async function getAcademyCategory(
  collectionSlug: string,
  categorySlug: string,
  locale?: string,
): Promise<AcademyCategoryWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.academyCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      categories: {
        where: { slug: categorySlug, isPublished: true },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
        },
      },
    },
  })

  if (!collection) return null

  const category = collection.categories[0]
  if (!category) return null

  const i18n = category.i18n[0]
  if (!i18n) return null

  const articleCount = await countAcademyArticlesByCategoryId(category.id)

  return {
    id: category.id,
    slug: category.slug,
    order: category.order,
    title: i18n.title,
    description: i18n.description ?? null,
    articleCount,
  }
}

/**
 * Prévisualisations d'articles publiés pour une « catégorie » (slug de tag ou ligne Academy legacy).
 */
export async function getAcademyArticles(
  collectionSlug: string,
  tagOrCategorySlug: string,
  locale?: string,
): Promise<AcademyArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.academyCollection.findUnique({
    where: { slug: collectionSlug },
    select: { id: true },
  })

  if (!collection) return []

  const all = await aggregateAcademyArticlePreviewsByCollectionId(collection.id, resolvedLocale)
  return all.filter((p) => p.collectionTags.includes(tagOrCategorySlug))
}

/**
 * Même agrégation que `getAcademyArticles`, mais à partir d'un `categoryId`
 * direct (utile pour les pages d'aperçu / vault).
 */
export async function getAcademyArticlesInCategory(
  categoryId: string,
  locale?: string,
): Promise<AcademyArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  return aggregateAcademyArticlePreviewsByCategoryId(categoryId, resolvedLocale)
}

/**
 * Détail article Academy : `/academy/[collection]/[academySlug]` (à plat ;
 * catégorie d’affichage dérivée des tags ou FK legacy).
 */
export async function getAcademyArticle(collectionSlug: string, articleSlug: string, locale?: string) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const article = await prisma.article.findFirst({
    where: {
      articleType: 'ACADEMY',
      status: 'PUBLISHED',
      academySlug: articleSlug,
      academyCollection: { slug: collectionSlug, isPublished: true },
    },
    include: {
      i18n: { where: { locale: resolvedLocale }, take: 1 },
      blocks: {
        orderBy: { order: 'asc' },
        include: {
          i18n: { where: { locale: resolvedLocale }, take: 1 },
        },
      },
      coverMedia: true,
      academyCollection: {
        include: { i18n: { where: { locale: resolvedLocale }, take: 1 } },
      },
      academyCategory: {
        include: { i18n: { where: { locale: resolvedLocale }, take: 1 } },
      },
    },
  })
  if (!article) return null

  const articleI18n = article.i18n[0]
  if (!articleI18n) return null

  const collection = article.academyCollection
  if (!collection) return null

  const groupingTags = deriveGroupingTags(article.collectionTags, article.academyCategory?.slug ?? null)
  const categorySlug = groupingTags[0] ?? article.academyCategory?.slug ?? 'general'
  const categoryTitle =
    article.academyCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(categorySlug)

  const blocksEnriched = await resolveArticleBlocksForPublic(prisma, article.blocks)

  return {
    id: article.id,
    slug: articleSlug,
    title: articleI18n.title,
    standfirst: articleI18n.standfirst ?? null,
    metaTitle: articleI18n.metaTitle,
    metaDescription: articleI18n.metaDescription,
    contentMarkdown: null as string | null,
    targetTags: normalizeAcademyTargetTags(article.targetTags),
    updatedAt: article.updatedAt,
    publishedAt: article.publishedAt ?? null,
    authorName: article.authorName,
    allowAnchors: article.allowAnchors,
    coverMedia: article.coverMedia,
    blocks: blocksEnriched,
    collection: {
      slug: collection.slug,
      title: collection.i18n[0]?.title || collection.slug,
      iconKey: collection.iconKey ?? null,
      colorHex: collection.colorHex ?? null,
    },
    category: {
      slug: categorySlug,
      title: categoryTitle,
    },
    locale: resolvedLocale,
  }
}

/**
 * Article Academy par slug "global" (sans connaître la collection/catégorie).
 * Utilisé par le mobile pour les liens de notification ou de partage.
 */
export async function getAcademyArticleByGlobalSlug(
  articleSlug: string,
  locale?: string,
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const hit = await prisma.article.findFirst({
    where: {
      articleType: 'ACADEMY',
      status: 'PUBLISHED',
      OR: [{ academySlug: articleSlug }, { slug: articleSlug }],
    },
    include: {
      academyCollection: { select: { slug: true } },
    },
  })
  if (!hit?.academyCollection?.slug) return null

  return getAcademyArticle(
    hit.academyCollection.slug,
    hit.academySlug ?? hit.slug,
    resolvedLocale,
  )
}

/**
 * Liste les articles Academy publiés qui ciblent un tag donné via
 * `target_tags` (JSONB tableau de `{type,id,slug,label}`).
 *
 * Filtre Postgres : `target_tags @> '[{"type":...,"id":...}]'::jsonb`.
 * Statut PUBLISHED uniquement.
 */
export async function getAcademyArticlesByTargetTag(
  tagType: AcademyTargetTagDTO['type'],
  tagId: string,
  locale?: string,
): Promise<Array<{
  id: string
  slug: string
  title: string
  standfirst: string | null
  updatedAt: Date
  publishedAt: Date | null
  collection: { slug: string; title: string }
  category: { slug: string; title: string }
}>> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const tagFilter = JSON.stringify([{ type: tagType, id: tagId }])

  const matchingIds = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
    `SELECT id FROM "articles" WHERE article_type = 'ACADEMY' AND status = 'PUBLISHED' AND target_tags @> $1::jsonb`,
    tagFilter,
  )
  if (matchingIds.length === 0) return []

  const articles = await prisma.article.findMany({
    where: { id: { in: matchingIds.map((r) => r.id) } },
    include: {
      i18n: { where: { locale: resolvedLocale }, take: 1 },
      academyCollection: { include: { i18n: { where: { locale: resolvedLocale }, take: 1 } } },
      academyCategory: { include: { i18n: { where: { locale: resolvedLocale }, take: 1 } } },
    },
    orderBy: { updatedAt: 'desc' },
  })

  const out: Array<{
    id: string
    slug: string
    title: string
    standfirst: string | null
    updatedAt: Date
    publishedAt: Date | null
    collection: { slug: string; title: string }
    category: { slug: string; title: string }
  }> = []

  for (const a of articles) {
    const i18n = a.i18n[0]
    if (!i18n) continue
    if (!a.academyCollection) continue
    const tags = deriveGroupingTags(a.collectionTags, a.academyCategory?.slug ?? null)
    const catSlug = tags[0] ?? a.academyCategory?.slug ?? 'general'
    const catTitle = a.academyCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(catSlug)
    out.push({
      id: a.id,
      slug: a.academySlug ?? a.slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      collection: {
        slug: a.academyCollection.slug,
        title: a.academyCollection.i18n[0]?.title ?? a.academyCollection.slug,
      },
      category: {
        slug: catSlug,
        title: catTitle,
      },
    })
  }

  return out
}
