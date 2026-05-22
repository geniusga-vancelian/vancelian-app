import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { buildBackendUrl } from '@/lib/backend'
import {
  getAnonymousBackendAdminId,
  signInternalBackendJwtAu,
} from '@/lib/backend-jwt'
import { effectiveIsCompanyNews, getCompanyNewsArticleIds } from '@/lib/blog/articleService'
import { pickArticleI18n } from '@/lib/blog/articleI18nFallback'
import { absolutizeMediaUrlForApiClient } from '@/lib/catalog/packagedCatalogHelpers'

type JsonRecord = Record<string, unknown>

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

async function resolveMediaUrl(mediaId: string | null | undefined): Promise<string | null> {
  if (!mediaId) return null
  const media = await prisma.media.findUnique({ where: { id: mediaId } })
  if (!media) return null
  try {
    return await getPresignedUrl(media.key, 3600)
  } catch {
    return media.url
  }
}

function extractCoverImage(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const obj = data as Record<string, unknown>
  const modules = obj.modules
  if (!Array.isArray(modules)) return null
  for (const m of modules) {
    if (m == null || typeof m !== 'object') continue
    const content = (m as Record<string, unknown>).content
    if (content == null || typeof content !== 'object') continue
    const c = content as Record<string, unknown>
    if (typeof c.imageUrl === 'string' && c.imageUrl.length > 0) return c.imageUrl
    if (Array.isArray(c.items) && c.items.length > 0) {
      const first = c.items[0]
      if (
        first != null &&
        typeof first === 'object' &&
        typeof (first as Record<string, unknown>).imageUrl === 'string'
      ) {
        return (first as Record<string, unknown>).imageUrl as string
      }
    }
  }
  return null
}

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as JsonRecord
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asInt(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return Math.floor(value)
  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function estimateReadingTime(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length
  if (words <= 0) return 1
  return Math.max(1, Math.round(words / 200))
}

/** Libellés localisés pour chaque slug de catégorie (ordre conservé) — pour les cartes marketing multi-tags. */
function categoryLabelsForSlugs(
  categorySlugs: unknown,
  labelBySlug: Map<string, string>,
): string[] {
  if (!Array.isArray(categorySlugs)) return []
  const out: string[] = []
  for (const raw of categorySlugs) {
    const slug = String(raw).trim()
    if (!slug) continue
    const label = labelBySlug.get(slug)
    if (label && label.trim().length > 0) out.push(label.trim())
  }
  return out
}

type BackendBundleInstrument = {
  id?: number
  symbol?: string
}

type BackendBundle = {
  id?: string
  name?: string
  description?: string | null
  asset_class?: string | null
  type?: string | null
  background_image?: string | null
  backgroundImage?: string | null
  image_url?: string | null
  imageUrl?: string | null
  instruments?: BackendBundleInstrument[]
}

async function fetchBackendBundles(): Promise<BackendBundle[]> {
  const token = signInternalBackendJwtAu(getAnonymousBackendAdminId(), '10m')

  const response = await fetch(buildBackendUrl('/api/bundles'), {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!response.ok) return []

  const json = await response.json().catch(() => [])
  if (!Array.isArray(json)) return []
  return json as BackendBundle[]
}

type FeedContext = { assetSlug?: string; publicOrigin?: string | null }

async function resolveFeedData(
  feedSchema: JsonRecord,
  locale: string,
  context?: FeedContext
) {
  const publicOrigin = context?.publicOrigin ?? null
  const absCover = (url: string | null | undefined): string =>
    absolutizeMediaUrlForApiClient(url ?? null, publicOrigin) ?? ''
  const feedType = asString(feedSchema.feedType).trim()
  const source = asRecord(feedSchema.source) ?? {}

  if (feedType === 'blog_crypto_asset') {
    // assetSlug = ticker crypto (ex. btc, eth) depuis le champ Related de l'article (article_links)
    // Uniquement articles de type news (exclut ANALYSIS et RESEARCH)
    const assetSlug = (context?.assetSlug ?? asString(source.categorySlug)).trim().toLowerCase()
    const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))
    const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })

    let allowedIds: string[] | undefined
    if (assetSlug) {
      const links = await prisma.articleLink.findMany({
        where: { kind: 'ASSET', targetId: assetSlug },
        select: { articleId: true },
      })
      allowedIds = links.map((l) => l.articleId)
      if (allowedIds.length === 0) {
        return { feedType, items: [] }
      }
    }

    const rawPool = await prisma.article.findMany({
      where: {
        status: ContentStatus.PUBLISHED,
        articleType: { notIn: ['ANALYSIS', 'RESEARCH'] },
        ...(allowedIds !== undefined ? { id: { in: allowedIds } } : {}),
      },
      orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
      include: {
        i18n: true,
        coverMedia: true,
      },
      take: Math.min(80, limit * 10),
    })
    const raw = rawPool
      .filter(
        (a) =>
          !effectiveIsCompanyNews({
            articleType: a.articleType,
            isCompanyNews: a.isCompanyNews,
            categorySlugs: a.categorySlugs,
          })
      )
      .slice(0, limit)

    const allCategorySlugs = raw
      .flatMap((a) => (Array.isArray(a.categorySlugs) ? a.categorySlugs : []))
      .map((v) => String(v))
      .filter(Boolean)
    const uniqueCategorySlugs = Array.from(new Set(allCategorySlugs))
    const categories =
      uniqueCategorySlugs.length > 0
        ? await prisma.articleCategory.findMany({
            where: { slug: { in: uniqueCategorySlugs } },
            include: { i18n: { where: { locale }, take: 1 } },
          })
        : []
    const categoryLabelBySlug = new Map<string, string>()
    for (const cat of categories) {
      categoryLabelBySlug.set(cat.slug, cat.i18n[0]?.label ?? cat.label)
    }

    const items = await Promise.all(
      raw.map(async (a) => {
        let coverUrl = a.coverMedia?.url || ''
        if (a.coverMedia?.key) {
          try {
            coverUrl = await getPresignedUrl(a.coverMedia.key, 3600)
          } catch {
            coverUrl = a.coverMedia.url
          }
        }
        const publishedRef = a.publishedAt ?? a.createdAt
        const catSlug =
          Array.isArray(a.categorySlugs) && a.categorySlugs.length > 0
            ? String(a.categorySlugs[0])
            : ''
        const categoryLabel = catSlug ? categoryLabelBySlug.get(catSlug) ?? '' : ''
        const categoryLabels = categoryLabelsForSlugs(a.categorySlugs, categoryLabelBySlug)
        const i18n = pickArticleI18n(a.i18n, locale)
        const standfirst = i18n?.standfirst ?? ''
        return {
          id: a.id,
          slug: a.slug,
          title: i18n?.title ?? a.slug,
          authorName: a.authorName,
          publishedAt: a.publishedAt?.toISOString() ?? null,
          publishedDate: publishedRef ? dateFormatter.format(publishedRef) : '',
          coverUrl: absCover(coverUrl),
          readingTime: estimateReadingTime(standfirst),
          categorySlug: catSlug || null,
          categoryLabel: categoryLabel || null,
          categoryLabels: categoryLabels.length > 0 ? categoryLabels : null,
          articleType: a.articleType,
          isCompanyNews: effectiveIsCompanyNews({
            articleType: a.articleType,
            isCompanyNews: a.isCompanyNews,
            categorySlugs: a.categorySlugs,
          }),
        }
      })
    )

    return { feedType, items }
  }

  if (feedType === 'research_crypto_asset') {
    // Research articles (ANALYSIS/RESEARCH) linked to the asset via Related (article_links)
    const assetSlug = (context?.assetSlug ?? asString(source.categorySlug)).trim().toLowerCase()
    const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))
    const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })

    let allowedIds: string[] | undefined
    if (assetSlug) {
      const links = await prisma.articleLink.findMany({
        where: { kind: 'ASSET', targetId: assetSlug },
        select: { articleId: true },
      })
      allowedIds = links.map((l) => l.articleId)
      if (allowedIds.length === 0) {
        return { feedType, items: [] }
      }
    }

    const raw = await prisma.article.findMany({
      where: {
        status: ContentStatus.PUBLISHED,
        articleType: { in: ['ANALYSIS', 'RESEARCH'] },
        ...(allowedIds !== undefined ? { id: { in: allowedIds } } : {}),
      },
      orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
      include: {
        i18n: true,
        coverMedia: true,
      },
      take: limit,
    })

    const allCategorySlugs = raw
      .flatMap((a) => (Array.isArray(a.categorySlugs) ? a.categorySlugs : []))
      .map((v) => String(v))
      .filter(Boolean)
    const uniqueCategorySlugs = Array.from(new Set(allCategorySlugs))
    const categories =
      uniqueCategorySlugs.length > 0
        ? await prisma.articleCategory.findMany({
            where: { slug: { in: uniqueCategorySlugs } },
            include: { i18n: { where: { locale }, take: 1 } },
          })
        : []
    const categoryLabelBySlug = new Map<string, string>()
    for (const cat of categories) {
      categoryLabelBySlug.set(cat.slug, cat.i18n[0]?.label ?? cat.label)
    }

    const items = await Promise.all(
      raw.map(async (a) => {
        let coverUrl = a.coverMedia?.url || ''
        if (a.coverMedia?.key) {
          try {
            coverUrl = await getPresignedUrl(a.coverMedia.key, 3600)
          } catch {
            coverUrl = a.coverMedia.url
          }
        }
        const publishedRef = a.publishedAt ?? a.createdAt
        const catSlug =
          Array.isArray(a.categorySlugs) && a.categorySlugs.length > 0
            ? String(a.categorySlugs[0])
            : ''
        const categoryLabel = catSlug ? categoryLabelBySlug.get(catSlug) ?? '' : ''
        const categoryLabels = categoryLabelsForSlugs(a.categorySlugs, categoryLabelBySlug)
        const i18n = pickArticleI18n(a.i18n, locale)
        const standfirst = i18n?.standfirst ?? ''
        return {
          id: a.id,
          slug: a.slug,
          title: i18n?.title ?? a.slug,
          authorName: a.authorName,
          publishedAt: a.publishedAt?.toISOString() ?? null,
          publishedDate: publishedRef ? dateFormatter.format(publishedRef) : '',
          coverUrl: absCover(coverUrl),
          readingTime: estimateReadingTime(standfirst),
          categorySlug: catSlug || null,
          categoryLabel: categoryLabel || null,
          categoryLabels: categoryLabels.length > 0 ? categoryLabels : null,
          articleType: a.articleType,
        }
      })
    )

    return { feedType, items }
  }

  /** Dashboard « Vancelian News » : uniquement les articles news entreprise (champ + tag legacy). */
  if (feedType === 'top10_news' || feedType === 'company_news') {
    const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))
    const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
    const companyIds = await getCompanyNewsArticleIds()
    const raw =
      companyIds.length === 0
        ? []
        : await prisma.article.findMany({
            where: {
              id: { in: companyIds },
              status: ContentStatus.PUBLISHED,
            },
            orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
            include: {
              i18n: true,
              coverMedia: true,
            },
            take: limit,
          })

    const allCategorySlugs = raw
      .flatMap((a) => (Array.isArray(a.categorySlugs) ? a.categorySlugs : []))
      .map((v) => String(v))
      .filter(Boolean)
    const uniqueCategorySlugs = Array.from(new Set(allCategorySlugs))
    const categories = uniqueCategorySlugs.length
      ? await prisma.articleCategory.findMany({
          where: { slug: { in: uniqueCategorySlugs } },
          include: {
            i18n: {
              where: { locale },
              take: 1,
            },
          },
        })
      : []
    const categoryLabelBySlug = new Map<string, string>()
    for (const cat of categories) {
      categoryLabelBySlug.set(cat.slug, cat.i18n[0]?.label ?? cat.label)
    }

    const items = await Promise.all(
      raw.map(async (a) => {
        let coverUrl = a.coverMedia?.url || ''
        if (a.coverMedia?.key) {
          try {
            coverUrl = await getPresignedUrl(a.coverMedia.key, 3600)
          } catch {
            coverUrl = a.coverMedia.url
          }
        }
        const publishedRef = a.publishedAt ?? a.createdAt
        const categorySlug = Array.isArray(a.categorySlugs) && a.categorySlugs.length > 0
          ? String(a.categorySlugs[0])
          : ''
        const categoryLabel = categorySlug ? (categoryLabelBySlug.get(categorySlug) ?? '') : ''
        const categoryLabels = categoryLabelsForSlugs(a.categorySlugs, categoryLabelBySlug)
        const i18n = pickArticleI18n(a.i18n, locale)
        const standfirst = i18n?.standfirst ?? ''
        return {
          id: a.id,
          slug: a.slug,
          title: i18n?.title ?? a.slug,
          authorName: a.authorName,
          publishedAt: a.publishedAt?.toISOString() ?? null,
          publishedDate: publishedRef ? dateFormatter.format(publishedRef) : '',
          coverUrl: absCover(coverUrl),
          readingTime: estimateReadingTime(standfirst),
          categorySlug: categorySlug || null,
          categoryLabel: categoryLabel || null,
          categoryLabels: categoryLabels.length > 0 ? categoryLabels : null,
          articleType: a.articleType,
          isCompanyNews: true,
        }
      })
    )

    return { feedType, items }
  }

  if (feedType === 'top10_research') {
    const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))
    const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
    const raw = await prisma.article.findMany({
      where: {
        status: ContentStatus.PUBLISHED,
        articleType: { in: ['ANALYSIS', 'RESEARCH'] },
      },
      orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
      include: {
        i18n: true,
        coverMedia: true,
      },
      take: limit,
    })

    const allCategorySlugs = raw
      .flatMap((a) => (Array.isArray(a.categorySlugs) ? a.categorySlugs : []))
      .map((v) => String(v))
      .filter(Boolean)
    const uniqueCategorySlugs = Array.from(new Set(allCategorySlugs))
    const categories = uniqueCategorySlugs.length
      ? await prisma.articleCategory.findMany({
          where: { slug: { in: uniqueCategorySlugs } },
          include: {
            i18n: {
              where: { locale },
              take: 1,
            },
          },
        })
      : []
    const categoryLabelBySlug = new Map<string, string>()
    for (const cat of categories) {
      categoryLabelBySlug.set(cat.slug, cat.i18n[0]?.label ?? cat.label)
    }

    const items = await Promise.all(
      raw.map(async (a) => {
        let coverUrl = a.coverMedia?.url || ''
        if (a.coverMedia?.key) {
          try {
            coverUrl = await getPresignedUrl(a.coverMedia.key, 3600)
          } catch {
            coverUrl = a.coverMedia.url
          }
        }
        const publishedRef = a.publishedAt ?? a.createdAt
        const categorySlug = Array.isArray(a.categorySlugs) && a.categorySlugs.length > 0
          ? String(a.categorySlugs[0])
          : ''
        const categoryLabel = categorySlug ? (categoryLabelBySlug.get(categorySlug) ?? '') : ''
        const categoryLabels = categoryLabelsForSlugs(a.categorySlugs, categoryLabelBySlug)
        const i18n = pickArticleI18n(a.i18n, locale)
        const standfirst = i18n?.standfirst ?? ''
        return {
          id: a.id,
          slug: a.slug,
          title: i18n?.title ?? a.slug,
          authorName: a.authorName,
          publishedAt: a.publishedAt?.toISOString() ?? null,
          publishedDate: publishedRef ? dateFormatter.format(publishedRef) : '',
          coverUrl: absCover(coverUrl),
          readingTime: estimateReadingTime(standfirst),
          categorySlug: categorySlug || null,
          categoryLabel: categoryLabel || null,
          categoryLabels: categoryLabels.length > 0 ? categoryLabels : null,
          articleType: a.articleType,
        }
      })
    )

    return { feedType, items }
  }

  if (feedType === 'blog_articles') {
    const categorySlug = asString(source.categorySlug).trim()
    const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))

    const raw = await prisma.article.findMany({
      where: { status: ContentStatus.PUBLISHED },
      orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
      include: {
        i18n: true,
      },
      take: 200,
    })

    const items = raw
      .filter((a) => {
        if (!categorySlug) return true
        const slugs = Array.isArray(a.categorySlugs) ? a.categorySlugs : []
        return slugs.map((v) => String(v)).includes(categorySlug)
      })
      .slice(0, limit)
      .map((a) => {
        const i18n = pickArticleI18n(a.i18n, locale)
        return {
          id: a.id,
          slug: a.slug,
          title: i18n?.title ?? a.slug,
          standfirst: i18n?.standfirst ?? '',
          publishedAt: a.publishedAt,
          articleType: a.articleType,
        }
      })

    return { feedType, items }
  }

  if (feedType === 'vaults_by_investment_type') {
    const investmentTypeSlug = asString(source.investmentTypeSlug).trim()
    const limit = Math.max(1, Math.min(100, asInt(source.limit, 20)))

    const pages = await prisma.page.findMany({
      where: { template: 'vault_builder' },
      include: {
        sections: {
          where: { key: 'vault_builder_v1' },
          include: {
            contents: {
              where: { locale, status: ContentStatus.PUBLISHED },
              take: 1,
            },
          },
          take: 1,
        },
      },
      orderBy: { createdAt: 'asc' },
    })

    const itemsRaw = await Promise.all(
      pages.map(async (p, index) => {
        const data = asRecord(p.sections[0]?.contents[0]?.data) ?? {}
        const headerMediaId = asString(data.headerMediaId).trim()
        const coverFromMedia = headerMediaId ? await resolveMediaUrl(headerMediaId) : null
        const coverFromModules = extractCoverImage(data)
        const coverImage =
          coverFromMedia ??
          coverFromModules ??
          `https://picsum.photos/seed/vault-${p.slug}/600/400`
        return {
          id: p.id,
          slug: p.slug,
          title: p.title ?? p.slug,
          description: p.description ?? null,
          urlPath: p.urlPath,
          coverImage,
          investmentTypeSlug: asString(data.investmentTypeSlug) || null,
          sortOrder: asInt(data.sortOrder, 999),
          dbOrder: index,
          pageCreatedAt: p.createdAt.toISOString(),
        }
      })
    )

    const filtered = itemsRaw.filter(
      (v) => !investmentTypeSlug || v.investmentTypeSlug === investmentTypeSlug
    )
    const ordered = [...filtered].sort((a, b) => {
      if (investmentTypeSlug) {
        const bySort = a.sortOrder - b.sortOrder
        if (bySort !== 0) return bySort
        return a.dbOrder - b.dbOrder
      }
      const catA = a.investmentTypeSlug ?? '__none__'
      const catB = b.investmentTypeSlug ?? '__none__'
      if (catA !== catB) return catA.localeCompare(catB)
      const bySort = a.sortOrder - b.sortOrder
      if (bySort !== 0) return bySort
      return a.dbOrder - b.dbOrder
    })
    const items = ordered
      .slice(0, limit)

    return { feedType, items }
  }

  if (feedType === 'crypto_bundles') {
    const limit = Math.max(1, Math.min(100, asInt(source.limit, 20)))
    const bundles = await fetchBackendBundles()
    const placeholderPrefix = asString(source.backgroundPlaceholderPrefix).trim() || 'crypto-bundle'

    const items = bundles
      .filter((b) => asString(b.asset_class).toLowerCase() === 'crypto')
      .map((b) => {
        const rawType = asString(b.type).trim()
        const classification = rawType || 'uncategorized'
        const instruments = Array.isArray(b.instruments) ? b.instruments : []
        const instrumentCount = instruments.length
        const imageUrl =
          asString(b.backgroundImage).trim() ||
          asString(b.background_image).trim() ||
          asString(b.imageUrl).trim() ||
          asString(b.image_url).trim() ||
          `https://picsum.photos/seed/${placeholderPrefix}-${asString(b.id)}/800/600`
        return {
          id: asString(b.id),
          slug: asString(b.id),
          title: asString(b.name) || 'Crypto bundle',
          description: asString(b.description) || null,
          classification,
          sortKey: `${classification}:${asString(b.name).toLowerCase()}`,
          imageUrl,
          redirectUrl: asString(b.id) ? `bundle://${asString(b.id)}` : '',
          instrumentCount,
          performance24h: null,
        }
      })
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
      .slice(0, limit)
      .map(({ sortKey: _sortKey, ...rest }) => rest)

    return { feedType, items }
  }

  if (feedType === 'top_crypto_mock') {
    // Feed mock en attendant le branchement market-data DB.
    return {
      feedType,
      popular: [
        { name: 'Bitcoin', ticker: 'BTC', price: '59 644 €', variationPercent: 3.25, redirectUrl: 'crypto://btc' },
        { name: 'Ether', ticker: 'ETH', price: '1 744,19 €', variationPercent: 4.61, redirectUrl: 'crypto://eth' },
        { name: 'Tether', ticker: 'USDT', price: '0,86 €', variationPercent: 0.22, redirectUrl: 'crypto://usdt' },
        { name: 'XRP', ticker: 'XRP', price: '1,17 €', variationPercent: 1.71, redirectUrl: 'crypto://xrp' },
        { name: 'USDC', ticker: 'USDC', price: '0,86 €', variationPercent: 0.21, redirectUrl: 'crypto://usdc' },
      ],
      topGainers: [
        { name: 'Solana', ticker: 'SOL', price: '178,90 €', variationPercent: 5.12, redirectUrl: 'crypto://sol' },
        { name: 'Avalanche', ticker: 'AVAX', price: '42,30 €', variationPercent: 4.28, redirectUrl: 'crypto://avax' },
        { name: 'Bitcoin', ticker: 'BTC', price: '59 644 €', variationPercent: 3.25, redirectUrl: 'crypto://btc' },
        { name: 'Ether', ticker: 'ETH', price: '1 744,19 €', variationPercent: 4.61, redirectUrl: 'crypto://eth' },
        { name: 'Cardano', ticker: 'ADA', price: '0,48 €', variationPercent: 1.56, redirectUrl: 'crypto://ada' },
      ],
      topLosers: [
        { name: 'Dogecoin', ticker: 'DOGE', price: '0,12 €', variationPercent: -2.15, redirectUrl: 'crypto://doge' },
        { name: 'XRP', ticker: 'XRP', price: '1,17 €', variationPercent: -1.20, redirectUrl: 'crypto://xrp' },
        { name: 'Polkadot', ticker: 'DOT', price: '7,85 €', variationPercent: -0.98, redirectUrl: 'crypto://dot' },
        { name: 'Chainlink', ticker: 'LINK', price: '14,20 €', variationPercent: -0.65, redirectUrl: 'crypto://link' },
        { name: 'Binance Coin', ticker: 'BNB', price: '612,40 €', variationPercent: -0.42, redirectUrl: 'crypto://bnb' },
      ],
    }
  }

  if (feedType === 'all_crypto_mock') {
    return {
      feedType,
      items: [
        { slug: 'btc', name: 'Bitcoin', ticker: 'BTC', price: '59 979 €', variationPercent: -1.47, marketCapRank: 1, redirectUrl: 'crypto://btc' },
        { slug: 'eth', name: 'Ether', ticker: 'ETH', price: '1 740,54 €', variationPercent: -2.18, marketCapRank: 2, redirectUrl: 'crypto://eth' },
        { slug: 'usdt', name: 'Tether', ticker: 'USDT', price: '0,86 €', variationPercent: 0.39, marketCapRank: 3, redirectUrl: 'crypto://usdt' },
        { slug: 'xrp', name: 'XRP', ticker: 'XRP', price: '1,18 €', variationPercent: -2.29, marketCapRank: 4, redirectUrl: 'crypto://xrp' },
        { slug: 'usdc', name: 'USDC', ticker: 'USDC', price: '0,86 €', variationPercent: 0.40, marketCapRank: 5, redirectUrl: 'crypto://usdc' },
        { slug: 'sol', name: 'Solana', ticker: 'SOL', price: '73,53 €', variationPercent: -2.65, marketCapRank: 6, redirectUrl: 'crypto://sol' },
        { slug: 'trx', name: 'Tron', ticker: 'TRX', price: '0,24 €', variationPercent: 1.38, marketCapRank: 7, redirectUrl: 'crypto://trx' },
        { slug: 'doge', name: 'Dogecoin', ticker: 'DOGE', price: '0,079 €', variationPercent: -6.21, marketCapRank: 8, redirectUrl: 'crypto://doge' },
        { slug: 'ada', name: 'Cardano', ticker: 'ADA', price: '0,22 €', variationPercent: -3.91, marketCapRank: 9, redirectUrl: 'crypto://ada' },
        { slug: 'dot', name: 'Polkadot', ticker: 'DOT', price: '7,85 €', variationPercent: -0.98, marketCapRank: 10, redirectUrl: 'crypto://dot' },
        { slug: 'link', name: 'Chainlink', ticker: 'LINK', price: '14,20 €', variationPercent: -0.65, marketCapRank: 11, redirectUrl: 'crypto://link' },
        { slug: 'bnb', name: 'Binance Coin', ticker: 'BNB', price: '612,40 €', variationPercent: -0.42, marketCapRank: 12, redirectUrl: 'crypto://bnb' },
        { slug: 'avax', name: 'Avalanche', ticker: 'AVAX', price: '42,30 €', variationPercent: 4.28, marketCapRank: 13, redirectUrl: 'crypto://avax' },
      ],
    }
  }

  return { feedType, items: [] as Array<Record<string, unknown>> }
}

/**
 * GET /api/mobile/flutter/widgets/[slug]?locale=fr
 * Retourne la définition d'un widget Builder + les feeds résolus.
 */
export async function GET(
  request: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const slug = (params.slug ?? '').trim()
    if (!slug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }
    const reqUrl = new URL(request.url)
    const { searchParams } = reqUrl
    const locale = searchParams.get('locale')?.trim() || 'fr'
    const assetSlug = searchParams.get('assetSlug')?.trim()?.toLowerCase() ?? undefined
    const publicOrigin = reqUrl.origin
    const context: FeedContext = { ...(assetSlug ? { assetSlug } : {}), publicOrigin }

    const widget = await prisma.dsComponent.findFirst({
      where: {
        slug,
        chapter: { slug: WIDGETS_CHAPTER_SLUG },
      },
      include: {
        chapter: {
          select: { slug: true, name: true },
        },
      },
    })
    if (!widget) {
      return NextResponse.json({ error: 'Widget not found' }, { status: 404 })
    }

    const schema = asRecord(widget.schemaJson) ?? {}
    const feedSlugs = Array.isArray(schema.feedSlugs)
      ? schema.feedSlugs.map((v) => String(v).trim()).filter(Boolean)
      : []

    const feeds = feedSlugs.length
      ? await prisma.dsComponent.findMany({
          where: {
            slug: { in: feedSlugs },
            chapter: { slug: FEEDS_CHAPTER_SLUG },
          },
        })
      : []

    const resolvedFeeds: Record<string, unknown> = {}
    for (const feed of feeds) {
      const feedSchema = asRecord(feed.schemaJson) ?? {}
      resolvedFeeds[feed.slug] = await resolveFeedData(feedSchema, locale, context)
    }

    return NextResponse.json({
      widget: {
        id: widget.id,
        slug: widget.slug,
        name: widget.name,
        schemaJson: widget.schemaJson,
      },
      feeds: resolvedFeeds,
      meta: { locale, assetSlug: assetSlug ?? null },
    })
  } catch (error) {
    console.error('[api/mobile/flutter/widgets/[slug]]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
