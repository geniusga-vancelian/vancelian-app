import type {
  PortalAcademyArticle,
  PortalAcademyCategory,
} from '@/lib/portal/academyHubTypes'
import { academyCategoryTone } from '@/lib/portal/academyFormat'
import type { PortalResearchItem } from '@/lib/portal/marketsTypes'
import { resolvePortalArticleHref } from '@/lib/portal/portalArticleRouting'

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function articleHref(slug: string, origin?: string): string {
  const path = resolvePortalArticleHref(slug)
  if (origin && !path.startsWith('http')) {
    return `${origin.replace(/\/$/, '')}${path}`
  }
  return path
}

function parseCategorySlugs(raw: unknown): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) {
    return raw.filter((value): value is string => typeof value === 'string' && value.length > 0)
  }
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw) as unknown
      return parseCategorySlugs(parsed)
    } catch {
      return []
    }
  }
  return []
}

function mapArticleCategories(payload: unknown): PortalAcademyCategory[] {
  const root = payload as Record<string, unknown> | null
  if (!root || !Array.isArray(root.articleCategories)) return []
  const out: PortalAcademyCategory[] = []
  for (const raw of root.articleCategories) {
    const row = raw as Record<string, unknown>
    const slug = String(row.slug ?? '').trim()
    const label = String(row.label ?? '').trim()
    const id = String(row.id ?? slug).trim()
    if (!slug || !label) continue
    out.push({ id, slug, label })
  }
  return out
}

function resolveArticleCategory(
  categorySlugs: string[],
  categories: PortalAcademyCategory[],
): { slug: string | null; label: string | null } {
  for (const slug of categorySlugs) {
    const match = categories.find((category) => category.slug === slug)
    if (match) return { slug: match.slug, label: match.label }
  }
  const fallbackSlug = categorySlugs[0] ?? null
  return { slug: fallbackSlug, label: fallbackSlug }
}

function normalizeArticleType(raw: unknown): PortalAcademyArticle['articleType'] {
  const value = String(raw ?? 'NEWS').toUpperCase()
  if (value === 'ANALYSIS') return 'ANALYSIS'
  if (value === 'RESEARCH') return 'RESEARCH'
  return 'NEWS'
}

function mapAcademyArticle(
  raw: unknown,
  options?: { origin?: string; categories?: PortalAcademyCategory[] },
): PortalAcademyArticle | null {
  const row = raw as Record<string, unknown> | null
  if (!row) return null

  const slug = String(row.slug ?? '').trim()
  const title = String(row.title ?? '').trim()
  if (!title) return null

  const categories = options?.categories ?? []
  const categorySlugs = parseCategorySlugs(row.categorySlugs ?? row.category_slugs)
  const { slug: categorySlug, label: categoryLabel } = resolveArticleCategory(categorySlugs, categories)
  const articleType = normalizeArticleType(row.articleType ?? row.article_type)

  const id = String(row.id ?? slug).trim() || slug
  return {
    id,
    slug,
    title,
    standfirst: String(row.standfirst ?? '').trim(),
    coverUrl: String(row.coverUrl ?? row.cover_url ?? '').trim(),
    authorName: String(row.authorName ?? row.author_name ?? 'Vancelian').trim(),
    publishedAt:
      typeof row.publishedAt === 'string'
        ? row.publishedAt
        : typeof row.published_at === 'string'
          ? row.published_at
          : null,
    readingTime: toNumber(row.readingTime ?? row.reading_time, 3),
    href: articleHref(slug, options?.origin),
    categorySlug,
    categoryLabel,
    categoryTone: academyCategoryTone(categorySlug),
    articleType,
  }
}

function isNewsArticle(raw: unknown): boolean {
  const row = raw as Record<string, unknown>
  const articleType = String(row.articleType ?? row.article_type ?? 'NEWS').toUpperCase()
  return articleType === 'NEWS'
}

function isResearchArticle(raw: unknown): boolean {
  const row = raw as Record<string, unknown>
  const articleType = String(row.articleType ?? row.article_type ?? '').toUpperCase()
  return articleType === 'ANALYSIS' || articleType === 'RESEARCH'
}

/** Feed blog (segment market) → hero + grille news portail. */
export function mapAcademyHubFromBlogFeed(
  payload: unknown,
  options?: { origin?: string },
): {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  news: PortalAcademyArticle[]
  categories: PortalAcademyCategory[]
} {
  const root = payload as Record<string, unknown> | null
  if (!root) {
    return { featured: null, highlighted: [], news: [], categories: [] }
  }

  const origin = options?.origin
  const categories = mapArticleCategories(root)
  const mapArticle = (raw: unknown) => mapAcademyArticle(raw, { origin, categories })

  const featuredRaw = root.featured
  const featured =
    featuredRaw && isNewsArticle(featuredRaw) ? mapArticle(featuredRaw) : null

  const highlighted: PortalAcademyArticle[] = []
  const excludeIds = new Set<string>()
  if (featured) excludeIds.add(featured.id)

  if (Array.isArray(root.highlighted)) {
    for (const raw of root.highlighted) {
      if (!isNewsArticle(raw)) continue
      const mapped = mapArticle(raw)
      if (!mapped || excludeIds.has(mapped.id)) continue
      excludeIds.add(mapped.id)
      highlighted.push(mapped)
    }
  }

  const news: PortalAcademyArticle[] = []
  const pushNews = (raw: unknown) => {
    if (!isNewsArticle(raw)) return
    const mapped = mapArticle(raw)
    if (!mapped || excludeIds.has(mapped.id)) return
    excludeIds.add(mapped.id)
    news.push(mapped)
  }

  if (Array.isArray(root.articles)) {
    for (const raw of root.articles) pushNews(raw)
  }

  return { featured, highlighted, news, categories }
}

/** Feed blog (segment analysis) → section research portail. */
export function mapAcademyResearchFromBlogFeed(
  payload: unknown,
  options?: { origin?: string; maxItems?: number },
): PortalResearchItem[] {
  const root = payload as Record<string, unknown> | null
  if (!root) return []

  const origin = options?.origin
  const maxItems = Math.min(Math.max(options?.maxItems ?? 8, 1), 16)
  const byId = new Map<string, PortalResearchItem>()

  const pushResearch = (raw: unknown) => {
    if (!isResearchArticle(raw)) return
    const row = raw as Record<string, unknown>
    const slug = String(row.slug ?? '').trim()
    const title = String(row.title ?? '').trim()
    if (!title) return
    const id = String(row.id ?? slug).trim() || slug
    if (byId.has(id)) return
    byId.set(id, {
      id,
      title,
      coverUrl: String(row.coverUrl ?? row.cover_url ?? '').trim(),
      readingTime: toNumber(row.readingTime ?? row.reading_time, 5),
      href: articleHref(slug, origin),
    })
  }

  if (root.featured) pushResearch(root.featured)
  if (Array.isArray(root.highlighted)) {
    for (const raw of root.highlighted) pushResearch(raw)
  }
  if (Array.isArray(root.articles)) {
    for (const raw of root.articles) pushResearch(raw)
  }

  return [...byId.values()].slice(0, maxItems)
}
