import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'
import { academyCategoryTone } from '@/lib/portal/academyFormat'
import {
  resolvePortalArticleHref,
  sanitizePortalArticleClientHref,
} from '@/lib/portal/portalArticleRouting'

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function articleHref(slug: string, origin?: string): string {
  return sanitizePortalArticleClientHref(resolvePortalArticleHref(slug, origin))
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

function normalizeArticleType(raw: unknown): PortalAcademyArticle['articleType'] {
  const value = String(raw ?? 'NEWS').toUpperCase()
  if (value === 'ANALYSIS') return 'ANALYSIS'
  if (value === 'ACADEMY') return 'ACADEMY'
  if (value === 'RESEARCH') return 'RESEARCH'
  return 'NEWS'
}

function normalizeIsCompanyNews(raw: unknown): boolean {
  return raw === true
}

function mapBlogArticle(
  raw: unknown,
  options?: { origin?: string; forceCompanyNews?: boolean },
): PortalAcademyArticle | null {
  const row = raw as Record<string, unknown> | null
  if (!row) return null

  const slug = String(row.slug ?? '').trim()
  const title = String(row.title ?? '').trim()
  if (!title) return null

  const categorySlugs = parseCategorySlugs(row.categorySlugs ?? row.category_slugs)
  const categorySlug = categorySlugs[0] ?? null
  const articleType = normalizeArticleType(row.articleType ?? row.article_type)
  const isCompanyNews =
    options?.forceCompanyNews === true
      ? true
      : normalizeIsCompanyNews(row.isCompanyNews ?? row.is_company_news)

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
    categoryLabel: categorySlug,
    categoryTone: academyCategoryTone(categorySlug),
    articleType,
    isCompanyNews,
  }
}

function isNewsArticle(raw: unknown): boolean {
  const row = raw as Record<string, unknown>
  const articleType = String(row.articleType ?? row.article_type ?? 'NEWS').toUpperCase()
  return articleType === 'NEWS'
}

function isAnalysisArticle(raw: unknown): boolean {
  const row = raw as Record<string, unknown>
  const articleType = String(row.articleType ?? row.article_type ?? '').toUpperCase()
  return articleType === 'ANALYSIS'
}

function collectNewsArticles(
  root: Record<string, unknown>,
  options?: { origin?: string; companyOnly?: boolean },
): PortalAcademyArticle[] {
  const origin = options?.origin
  const companyOnly = options?.companyOnly === true
  const mapArticle = (raw: unknown) =>
    mapBlogArticle(raw, { origin, forceCompanyNews: companyOnly })

  const out: PortalAcademyArticle[] = []
  const excludeIds = new Set<string>()

  const push = (raw: unknown) => {
    if (!isNewsArticle(raw)) return
    const mapped = mapArticle(raw)
    if (!mapped) return
    if (!companyOnly && mapped.isCompanyNews) return
    if (excludeIds.has(mapped.id)) return
    excludeIds.add(mapped.id)
    out.push(mapped)
  }

  if (root.featured) push(root.featured)
  if (Array.isArray(root.highlighted)) {
    for (const raw of root.highlighted) push(raw)
  }
  if (Array.isArray(root.companyNews)) {
    for (const raw of root.companyNews) push(raw)
  }
  if (Array.isArray(root.articles)) {
    for (const raw of root.articles) push(raw)
  }

  return out
}

function collectAnalysisArticles(
  root: Record<string, unknown>,
  options?: { origin?: string },
): PortalAcademyArticle[] {
  const origin = options?.origin
  const out: PortalAcademyArticle[] = []
  const excludeIds = new Set<string>()

  const push = (raw: unknown) => {
    if (!isAnalysisArticle(raw)) return
    const mapped = mapBlogArticle(raw, { origin })
    if (!mapped || excludeIds.has(mapped.id)) return
    excludeIds.add(mapped.id)
    mapped.categoryLabel = 'Analysis'
    mapped.categorySlug = 'analysis'
    mapped.categoryTone = 'blue'
    out.push(mapped)
  }

  if (root.featured) push(root.featured)
  if (Array.isArray(root.highlighted)) {
    for (const raw of root.highlighted) push(raw)
  }
  if (Array.isArray(root.articles)) {
    for (const raw of root.articles) push(raw)
  }

  return out
}

/** Feed blog (segment market) → hero + market news. */
export function mapAcademyHubFromBlogFeed(
  payload: unknown,
  options?: { origin?: string },
): {
  featured: PortalAcademyArticle | null
  highlighted: PortalAcademyArticle[]
  marketNews: PortalAcademyArticle[]
} {
  const root = payload as Record<string, unknown> | null
  if (!root) {
    return { featured: null, highlighted: [], marketNews: [] }
  }

  const origin = options?.origin
  const mapArticle = (raw: unknown) => mapBlogArticle(raw, { origin })

  const featuredRaw = root.featured
  const featuredCandidate = featuredRaw && isNewsArticle(featuredRaw) ? mapArticle(featuredRaw) : null
  const featured =
    featuredCandidate && !featuredCandidate.isCompanyNews ? featuredCandidate : null

  const highlighted: PortalAcademyArticle[] = []
  const excludeIds = new Set<string>()
  if (featured) excludeIds.add(featured.id)

  if (Array.isArray(root.highlighted)) {
    for (const raw of root.highlighted) {
      if (!isNewsArticle(raw)) continue
      const mapped = mapArticle(raw)
      if (!mapped || mapped.isCompanyNews || excludeIds.has(mapped.id)) continue
      excludeIds.add(mapped.id)
      highlighted.push(mapped)
    }
  }

  const marketNews: PortalAcademyArticle[] = []
  const pushMarket = (raw: unknown) => {
    if (!isNewsArticle(raw)) return
    const mapped = mapArticle(raw)
    if (!mapped || mapped.isCompanyNews || excludeIds.has(mapped.id)) return
    excludeIds.add(mapped.id)
    marketNews.push(mapped)
  }

  if (Array.isArray(root.articles)) {
    for (const raw of root.articles) pushMarket(raw)
  }

  return { featured, highlighted, marketNews }
}

/** Feed blog (segment company) → actualités Vancelian. */
export function mapVancelianNewsFromBlogFeed(
  payload: unknown,
  options?: { origin?: string },
): PortalAcademyArticle[] {
  const root = payload as Record<string, unknown> | null
  if (!root) return []
  return collectNewsArticles(root, { origin: options?.origin, companyOnly: true })
}

/** Feed blog (segment analysis) → analyses (type ANALYSIS uniquement). */
export function mapAnalysisFromBlogFeed(
  payload: unknown,
  options?: { origin?: string },
): PortalAcademyArticle[] {
  const root = payload as Record<string, unknown> | null
  if (!root) return []
  return collectAnalysisArticles(root, options)
}
