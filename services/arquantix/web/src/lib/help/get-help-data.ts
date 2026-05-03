import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import { resolveArticleBlocksForPublic } from '@/lib/blog/normalizeArticleBlocks'
import { tagSlugToDisplayTitle, deriveGroupingTags } from '@/lib/articles/collectionTags'


/**
 * Tag normalisé tel qu'attendu par les consommateurs publics (web + mobile).
 * Les routes `/api/help/articles/by-tag` et le payload `targetTags` des
 * previews respectent ce format.
 */
export interface HelpTargetTagDTO {
  type: 'THEMATIC_CATEGORY' | 'INVESTMENT_TYPE' | 'EXCLUSIVE_OFFER'
  id: string
  slug: string
  label: string
}

const VALID_TARGET_TAG_TYPES = new Set<HelpTargetTagDTO['type']>([
  'THEMATIC_CATEGORY',
  'INVESTMENT_TYPE',
  'EXCLUSIVE_OFFER',
])

/**
 * Parse les `target_tags` stockés en JSON (tableau d'objets `{type,id,slug,label}`)
 * en filtrant les entrées invalides. Tolère un input string (ré-encodé JSON)
 * comme un input array.
 */
export function normalizeHelpTargetTags(raw: unknown): HelpTargetTagDTO[] {
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
      VALID_TARGET_TAG_TYPES.has(row.type as HelpTargetTagDTO['type']) &&
      typeof row.id === 'string' &&
      typeof row.slug === 'string' &&
      typeof row.label === 'string',
    )
    .map((row) => ({
      type: row.type as HelpTargetTagDTO['type'],
      id: String(row.id),
      slug: String(row.slug),
      label: String(row.label),
    }))
}

/**
 * Agrégation Help unifiée pour les listings publics : retourne d'abord les
 * `Article(articleType='HELP')` rattachés à une catégorie, puis complète
 * avec les `HelpArticle` legacy non encore migrés (dédup par `helpSlug`).
 *
 * Phase 3.3 : tant que `migrate-help-to-article.ts --apply` n'a pas tourné
 * en prod, on garde la lecture legacy pour ne rien casser. Cette fonction
 * fait le merge de manière transparente.
 */
async function aggregateHelpArticlePreviewsByCollectionId(
  collectionId: string,
  locale: string,
): Promise<HelpArticlePreview[]> {
  const [unifiedArticles, legacyArticles] = await Promise.all([
    prisma.article.findMany({
      where: {
        articleType: 'HELP',
        status: 'PUBLISHED',
        helpCollectionId: collectionId,
      },
      include: {
        i18n: { where: { locale }, take: 1 },
        helpCategory: { select: { slug: true } },
      },
      orderBy: { publishedAt: 'desc' },
    }),
    prisma.helpArticle.findMany({
      where: {
        status: 'PUBLISHED',
        category: { collectionId, isPublished: true },
      },
      include: {
        i18n: { where: { locale }, take: 1 },
        category: { select: { slug: true } },
      },
      orderBy: { publishedAt: 'desc' },
    }),
  ])

  const previews: HelpArticlePreview[] = []
  const takenHelpSlugs = new Set<string>()

  for (const a of unifiedArticles) {
    const i18n = a.i18n[0]
    if (!i18n) continue
    const slug = a.helpSlug ?? a.slug
    takenHelpSlugs.add(slug)
    previews.push({
      id: a.id,
      slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      targetTags: normalizeHelpTargetTags(a.targetTags),
      collectionTags: deriveGroupingTags(a.collectionTags, a.helpCategory?.slug ?? null),
    })
  }

  for (const a of legacyArticles) {
    if (takenHelpSlugs.has(a.slug)) continue
    const i18n = a.i18n[0]
    if (!i18n) continue
    previews.push({
      id: a.id,
      slug: a.slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      targetTags: normalizeHelpTargetTags(a.targetTags),
      collectionTags: deriveGroupingTags(null, a.category.slug),
    })
  }

  return previews
}

async function aggregateHelpArticlePreviewsByCategoryId(
  categoryId: string,
  locale: string,
): Promise<HelpArticlePreview[]> {
  const cat = await prisma.helpCategory.findUnique({
    where: { id: categoryId },
    select: { collectionId: true, slug: true },
  })
  if (!cat) return []
  const all = await aggregateHelpArticlePreviewsByCollectionId(cat.collectionId, locale)
  return all.filter((p) => p.collectionTags.includes(cat.slug))
}

/**
 * Compte Help unifié pour une catégorie : Article(HELP) + HelpArticle non
 * encore migrés (dédup `helpSlug`). Statut PUBLISHED uniquement.
 */
async function countHelpArticlesByCategoryId(categoryId: string): Promise<number> {
  const cat = await prisma.helpCategory.findUnique({
    where: { id: categoryId },
    select: { slug: true, collectionId: true },
  })
  if (!cat) return 0

  const unifiedRows = await prisma.article.findMany({
    where: {
      articleType: 'HELP',
      status: 'PUBLISHED',
      helpCollectionId: cat.collectionId,
    },
    select: {
      helpSlug: true,
      slug: true,
      collectionTags: true,
      helpCategory: { select: { slug: true } },
    },
  })

  const taken = new Set<string>()
  let count = 0
  for (const row of unifiedRows) {
    const tags = deriveGroupingTags(row.collectionTags, row.helpCategory?.slug ?? null)
    if (!tags.includes(cat.slug)) continue
    taken.add(row.helpSlug ?? row.slug)
    count++
  }

  const legacy = await prisma.helpArticle.findMany({
    where: { categoryId, status: 'PUBLISHED' },
    select: { slug: true },
  })
  for (const l of legacy) if (!taken.has(l.slug)) count++

  return count
}

async function countHelpArticlesByCollectionId(collectionId: string): Promise<number> {
  const unified = await prisma.article.findMany({
    where: { articleType: 'HELP', status: 'PUBLISHED', helpCollectionId: collectionId },
    select: { helpSlug: true, slug: true },
  })
  const taken = new Set(unified.map((a) => a.helpSlug ?? a.slug))
  let count = unified.length
  const legacy = await prisma.helpArticle.findMany({
    where: { status: 'PUBLISHED', category: { collectionId } },
    select: { slug: true },
  })
  for (const l of legacy) if (!taken.has(l.slug)) count++
  return count
}

export interface HelpCollectionWithCount {
  id: string
  slug: string
  order: number
  title: string
  subtitle: string | null
  description: string | null
  iconKey: string | null
  colorHex: string | null
  /** URL publique de la vignette collection (même résolution que les covers article). */
  coverImageUrl: string | null
  articleCount: number
}

export interface HelpCategoryWithCount {
  id: string
  slug: string
  order: number
  title: string
  description: string | null
  articleCount: number
}

export interface HelpArticlePreview {
  id: string
  slug: string
  title: string
  standfirst: string | null
  updatedAt: Date
  publishedAt: Date | null
  targetTags: HelpTargetTagDTO[]
  /** Slugs « tags catégorie » pour regroupement sous la collection (dérivés aussi du FK legacy). */
  collectionTags: string[]
}

/**
 * Get all published collections with article counts
 */
export async function getHelpCollections(locale?: string): Promise<HelpCollectionWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collections = await prisma.helpCollection.findMany({
    where: { isPublished: true },
    orderBy: { order: 'asc' },
    include: {
      coverMedia: true,
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
    },
  })

  const results = await Promise.all(
    collections.map(async (collection): Promise<HelpCollectionWithCount | null> => {
      const i18n = collection.i18n[0]
      if (!i18n) return null

      const articleCount = await countHelpArticlesByCollectionId(collection.id)

      const coverImageUrl =
        (await resolveArticleCoverUrlForPublic(collection.coverMedia)) || null

      return {
        id: collection.id,
        slug: collection.slug,
        order: collection.order,
        title: i18n.title,
        subtitle: i18n.subtitle ?? null,
        description: i18n.description ?? null,
        iconKey: collection.iconKey ?? null,
        colorHex: collection.colorHex ?? null,
        coverImageUrl,
        articleCount,
      }
    }),
  )
  return results.filter((c): c is HelpCollectionWithCount => c !== null)
}

/**
 * Get collection by slug with categories
 */
export async function getHelpCollection(
  slug: string,
  locale?: string
): Promise<HelpCollectionWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug },
    include: {
      coverMedia: true,
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
    },
  })

  if (!collection || !collection.isPublished) return null
  const i18n = collection.i18n[0]
  if (!i18n) return null

  const articleCount = await countHelpArticlesByCollectionId(collection.id)

  const coverImageUrl =
    (await resolveArticleCoverUrlForPublic(collection.coverMedia)) || null

  return {
    id: collection.id,
    slug: collection.slug,
    order: collection.order,
    title: i18n.title,
    subtitle: i18n.subtitle ?? null,
    description: i18n.description ?? null,
    iconKey: collection.iconKey ?? null,
    colorHex: collection.colorHex ?? null,
    coverImageUrl,
    articleCount,
  }
}

/**
 * Get categories for a collection
 */
export async function getHelpCategories(
  collectionSlug: string,
  locale?: string
): Promise<HelpCategoryWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
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
      const articleCount = await countHelpArticlesByCategoryId(category.id)
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
  return cats.filter((c): c is HelpCategoryWithCount => c !== null)
}

/**
 * Get collection by slug with categories (for categories grid)
 */
export async function getHelpCollectionWithCategories(
  collectionSlug: string,
  locale?: string
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
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
 * Get category by slug
 */
export async function getHelpCategory(
  collectionSlug: string,
  categorySlug: string,
  locale?: string
): Promise<HelpCategoryWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
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

  const articleCount = await countHelpArticlesByCategoryId(category.id)

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
 * Liste les articles d'une collection dont au moins un « tag catégorie »
 * correspond au slug passé (y compris l’ancien slug de catégorie Help).
 */
export async function getHelpArticles(
  collectionSlug: string,
  tagOrCategorySlug: string,
  locale?: string,
): Promise<HelpArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    select: { id: true },
  })
  if (!collection) return []

  const all = await aggregateHelpArticlePreviewsByCollectionId(collection.id, resolvedLocale)
  return all.filter((p) => p.collectionTags.includes(tagOrCategorySlug))
}

/**
 * Tous les articles Help publiés d'une collection (unifié + legacy), tri date décroissante.
 */
export async function getHelpArticlesAllInCollection(
  collectionSlug: string,
  locale?: string,
): Promise<HelpArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    select: { id: true },
  })
  if (!collection) return []

  const all = await aggregateHelpArticlePreviewsByCollectionId(collection.id, resolvedLocale)
  return all.sort((x, y) => (y.publishedAt?.getTime() ?? 0) - (x.publishedAt?.getTime() ?? 0))
}

export interface HelpCollectionBrowseTagGroup {
  slug: string
  title: string
  articleCount: number
}

export interface HelpCollectionBrowseResult {
  collection: { slug: string; title: string }
  displayMode: 'flat' | 'grouped'
  tagGroups: HelpCollectionBrowseTagGroup[]
  articles: HelpArticlePreview[]
}

/**
 * Parcours mobile / hub : regroupements = union des `collectionTags` des articles (sans doublon).
 * Mode `flat` si un seul slug distinct au total (ex. tout le monde en `general`).
 */
export async function getHelpCollectionBrowse(
  collectionSlug: string,
  locale?: string,
): Promise<HelpCollectionBrowseResult | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collectionRow = await prisma.helpCollection.findUnique({
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

  if (!collectionRow || !collectionRow.isPublished) return null
  const collI18n = collectionRow.i18n[0]
  if (!collI18n) return null

  const previews = await aggregateHelpArticlePreviewsByCollectionId(collectionRow.id, resolvedLocale)

  const slugSet = new Set<string>()
  for (const p of previews) {
    for (const t of p.collectionTags) slugSet.add(t)
  }

  const titleBySlug = new Map<string, string>()
  const orderBySlug = new Map<string, number>()
  for (const c of collectionRow.categories) {
    titleBySlug.set(c.slug, c.i18n[0]?.title ?? tagSlugToDisplayTitle(c.slug))
    orderBySlug.set(c.slug, c.order)
  }

  const uniqueSlugs = [...slugSet].sort((a, b) => {
    const oa = orderBySlug.has(a) ? orderBySlug.get(a)! : 999
    const ob = orderBySlug.has(b) ? orderBySlug.get(b)! : 999
    if (oa !== ob) return oa - ob
    return a.localeCompare(b)
  })

  const displayMode: 'flat' | 'grouped' = uniqueSlugs.length <= 1 ? 'flat' : 'grouped'

  const collectionPayload = {
    slug: collectionRow.slug,
    title: collI18n.title,
  }

  if (displayMode === 'flat') {
    return {
      collection: collectionPayload,
      displayMode: 'flat',
      tagGroups: [],
      articles: previews.sort(
        (x, y) => (y.publishedAt?.getTime() ?? 0) - (x.publishedAt?.getTime() ?? 0),
      ),
    }
  }

  const tagGroups: HelpCollectionBrowseTagGroup[] = uniqueSlugs.map((slug) => ({
    slug,
    title: titleBySlug.get(slug) ?? tagSlugToDisplayTitle(slug),
    articleCount: previews.filter((p) => p.collectionTags.includes(slug)).length,
  }))

  return {
    collection: collectionPayload,
    displayMode: 'grouped',
    tagGroups,
    articles: [],
  }
}

/**
 * Regroupe les articles publiés sous une collection par leur premier tag
 * catégorie (titres alignés sur les catégories Help existantes quand le slug matche).
 */
export async function getHelpPublishedGroupedForCollection(
  collectionSlug: string,
  locale?: string,
): Promise<Array<{ tagSlug: string; title: string; articles: HelpArticlePreview[] }>> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
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

  if (!collection || !collection.isPublished) return []

  const titleBySlug = new Map<string, string>()
  const orderBySlug = new Map<string, number>()
  for (const c of collection.categories) {
    titleBySlug.set(c.slug, c.i18n[0]?.title ?? tagSlugToDisplayTitle(c.slug))
    orderBySlug.set(c.slug, c.order)
  }

  const previews = await aggregateHelpArticlePreviewsByCollectionId(collection.id, resolvedLocale)

  const groupsMap = new Map<string, HelpArticlePreview[]>()
  for (const p of previews) {
    const primary = p.collectionTags.length > 0 ? p.collectionTags[0] : 'general'
    const bucket = groupsMap.get(primary) ?? []
    bucket.push(p)
    groupsMap.set(primary, bucket)
  }

  const tagSlugs = [...groupsMap.keys()].sort((a, b) => {
    const oa = orderBySlug.has(a) ? orderBySlug.get(a)! : 999
    const ob = orderBySlug.has(b) ? orderBySlug.get(b)! : 999
    if (oa !== ob) return oa - ob
    return a.localeCompare(b)
  })

  return tagSlugs.map((tagSlug) => ({
    tagSlug,
    title: titleBySlug.get(tagSlug) ?? tagSlugToDisplayTitle(tagSlug),
    articles: (groupsMap.get(tagSlug) ?? []).sort(
      (x, y) => (y.publishedAt?.getTime() ?? 0) - (x.publishedAt?.getTime() ?? 0),
    ),
  }))
}

/**
 * Get articles in a category by category ID (mêmes règles d'agrégation).
 */
export async function getHelpArticlesInCategory(
  categoryId: string,
  locale?: string
): Promise<HelpArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const category = await prisma.helpCategory.findUnique({
    where: { id: categoryId },
    select: { id: true },
  })
  if (!category) return []

  return aggregateHelpArticlePreviewsByCategoryId(category.id, resolvedLocale)
}

/**
 * Détail article Help : `/help/[collection]/[helpSlug]` (schéma à plat ;
 * catégorie d’affichage dérivée des tags ou du FK legacy).
 */
export async function getHelpArticle(collectionSlug: string, articleSlug: string, locale?: string) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const unified = await readHelpArticleFromUnifiedFlat(collectionSlug, articleSlug, resolvedLocale)
  if (unified) return unified

  return readHelpArticleFromLegacyFlat(collectionSlug, articleSlug, resolvedLocale)
}

async function readHelpArticleFromUnifiedFlat(
  collectionSlug: string,
  articleSlug: string,
  resolvedLocale: string,
) {
  const article = await prisma.article.findFirst({
    where: {
      articleType: 'HELP',
      status: 'PUBLISHED',
      helpSlug: articleSlug,
      helpCollection: { slug: collectionSlug, isPublished: true },
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
      helpCollection: {
        include: { i18n: { where: { locale: resolvedLocale }, take: 1 } },
      },
      helpCategory: {
        include: { i18n: { where: { locale: resolvedLocale }, take: 1 } },
      },
    },
  })
  if (!article) return null

  const articleI18n = article.i18n[0]
  if (!articleI18n) return null

  const collection = article.helpCollection
  if (!collection) return null

  const groupingTags = deriveGroupingTags(article.collectionTags, article.helpCategory?.slug ?? null)
  const categorySlug = groupingTags[0] ?? article.helpCategory?.slug ?? 'general'
  const categoryTitle =
    article.helpCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(categorySlug)

  const blocksEnriched = await resolveArticleBlocksForPublic(prisma, article.blocks)

  return {
    id: article.id,
    slug: articleSlug,
    title: articleI18n.title,
    standfirst: articleI18n.standfirst ?? null,
    metaTitle: articleI18n.metaTitle,
    metaDescription: articleI18n.metaDescription,
    contentMarkdown: null as string | null,
    targetTags: normalizeHelpTargetTags(article.targetTags),
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

async function readHelpArticleFromLegacyFlat(collectionSlug: string, articleSlug: string, resolvedLocale: string) {
  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      i18n: { where: { locale: resolvedLocale }, take: 1 },
      categories: {
        where: { isPublished: true },
        include: {
          i18n: { where: { locale: resolvedLocale }, take: 1 },
          articles: {
            where: { slug: articleSlug, status: 'PUBLISHED' },
            include: {
              i18n: { where: { locale: resolvedLocale }, take: 1 },
              blocks: {
                where: { locale: resolvedLocale },
                orderBy: { order: 'asc' },
              },
              coverMedia: true,
            },
          },
        },
      },
    },
  })

  if (!collection || !collection.isPublished) return null

  const category = collection.categories.find((c) => c.articles.length > 0)
  if (!category) return null

  const article = category.articles[0]
  if (!article) return null

  const articleI18n = article.i18n[0]
  if (!articleI18n) return null

  const collectionI18n = collection.i18n[0]
  const categoryI18n = category.i18n[0]

  const blocksEnriched = await resolveArticleBlocksForPublic(prisma, article.blocks)

  return {
    id: article.id,
    slug: article.slug,
    title: articleI18n.title,
    standfirst: articleI18n.standfirst ?? null,
    metaTitle: articleI18n.metaTitle,
    metaDescription: articleI18n.metaDescription,
    contentMarkdown: articleI18n.contentMarkdown ?? null,
    targetTags: normalizeHelpTargetTags(article.targetTags),
    updatedAt: article.updatedAt,
    publishedAt: article.publishedAt ?? null,
    authorName: article.authorName,
    allowAnchors: article.allowAnchors,
    coverMedia: article.coverMedia,
    blocks: blocksEnriched,
    collection: {
      slug: collection.slug,
      title: collectionI18n?.title || collection.slug,
      iconKey: collection.iconKey ?? null,
      colorHex: collection.colorHex ?? null,
    },
    category: {
      slug: category.slug,
      title: categoryI18n?.title || category.slug,
    },
    locale: resolvedLocale,
  }
}

/**
 * Recherche un article Help par slug "global" (sans connaître la
 * collection/categorie). Tente d'abord `Article(HELP)` (par `helpSlug` puis
 * fallback sur `slug`), puis `HelpArticle` legacy. Idempotent vs
 * `getHelpArticle` : retourne la même shape.
 */
export async function getHelpArticleByGlobalSlug(
  articleSlug: string,
  locale?: string,
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const unifiedHit = await prisma.article.findFirst({
    where: {
      articleType: 'HELP',
      status: 'PUBLISHED',
      OR: [{ helpSlug: articleSlug }, { slug: articleSlug }],
    },
    include: {
      helpCollection: { select: { slug: true } },
      helpCategory: { select: { slug: true } },
    },
  })
  if (unifiedHit?.helpCollection?.slug) {
    const detail = await readHelpArticleFromUnifiedFlat(
      unifiedHit.helpCollection.slug,
      unifiedHit.helpSlug ?? unifiedHit.slug,
      resolvedLocale,
    )
    if (detail) return detail
  }

  const legacyHit = await prisma.helpArticle.findFirst({
    where: { slug: articleSlug, status: 'PUBLISHED' },
    include: {
      category: {
        include: {
          collection: { select: { slug: true } },
        },
      },
    },
  })
  if (legacyHit?.category?.collection?.slug) {
    return readHelpArticleFromLegacyFlat(
      legacyHit.category.collection.slug,
      legacyHit.slug,
      resolvedLocale,
    )
  }

  return null
}

/**
 * Liste les articles Help (unifié + legacy) qui ciblent un tag donné via
 * `target_tags` (JSONB tableau de `{type,id,slug,label}`). Dédup par helpSlug.
 *
 * Filtre Postgres : `target_tags @> '[{"type":...,"id":...}]'::jsonb`. Sur le
 * legacy `helpArticle` cette colonne porte le même format JSON, donc même
 * filtre. Statut PUBLISHED uniquement.
 */
export async function getHelpArticlesByTargetTag(
  tagType: HelpTargetTagDTO['type'],
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

  const [unifiedRows, legacyRows] = await Promise.all([
    prisma.$queryRawUnsafe<Array<{ id: string }>>(
      `SELECT id FROM "articles" WHERE article_type = 'HELP' AND status = 'PUBLISHED' AND target_tags @> $1::jsonb`,
      tagFilter,
    ),
    prisma.$queryRawUnsafe<Array<{ id: string }>>(
      `SELECT id FROM "help_articles" WHERE status = 'PUBLISHED' AND target_tags @> $1::jsonb`,
      tagFilter,
    ),
  ])

  const [unifiedArticles, legacyArticles] = await Promise.all([
    unifiedRows.length === 0
      ? Promise.resolve([])
      : prisma.article.findMany({
          where: { id: { in: unifiedRows.map((r) => r.id) } },
          include: {
            i18n: { where: { locale: resolvedLocale }, take: 1 },
            helpCollection: { include: { i18n: { where: { locale: resolvedLocale }, take: 1 } } },
            helpCategory: { include: { i18n: { where: { locale: resolvedLocale }, take: 1 } } },
          },
          orderBy: { updatedAt: 'desc' },
        }),
    legacyRows.length === 0
      ? Promise.resolve([])
      : prisma.helpArticle.findMany({
          where: { id: { in: legacyRows.map((r) => r.id) } },
          include: {
            i18n: { where: { locale: resolvedLocale }, take: 1 },
            category: {
              include: {
                i18n: { where: { locale: resolvedLocale }, take: 1 },
                collection: {
                  include: { i18n: { where: { locale: resolvedLocale }, take: 1 } },
                },
              },
            },
          },
          orderBy: { updatedAt: 'desc' },
        }),
  ])

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
  const taken = new Set<string>()

  for (const a of unifiedArticles) {
    const i18n = a.i18n[0]
    if (!i18n) continue
    if (!a.helpCollection) continue
    const slug = a.helpSlug ?? a.slug
    taken.add(slug)
    const tags = deriveGroupingTags(a.collectionTags, a.helpCategory?.slug ?? null)
    const catSlug = tags[0] ?? a.helpCategory?.slug ?? 'general'
    const catTitle = a.helpCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(catSlug)
    out.push({
      id: a.id,
      slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      collection: {
        slug: a.helpCollection.slug,
        title: a.helpCollection.i18n[0]?.title ?? a.helpCollection.slug,
      },
      category: {
        slug: catSlug,
        title: catTitle,
      },
    })
  }

  for (const a of legacyArticles) {
    if (taken.has(a.slug)) continue
    const i18n = a.i18n[0]
    if (!i18n) continue
    if (!a.category?.collection) continue
    out.push({
      id: a.id,
      slug: a.slug,
      title: i18n.title,
      standfirst: i18n.standfirst ?? null,
      updatedAt: a.updatedAt,
      publishedAt: a.publishedAt ?? null,
      collection: {
        slug: a.category.collection.slug,
        title: a.category.collection.i18n[0]?.title ?? a.category.collection.slug,
      },
      category: {
        slug: a.category.slug,
        title: a.category.i18n[0]?.title ?? a.category.slug,
      },
    })
  }

  return out
}

