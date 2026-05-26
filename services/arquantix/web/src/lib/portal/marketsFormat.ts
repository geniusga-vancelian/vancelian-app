import type {
  MarketQuoteUpdate,
  PortalCryptoAsset,
  PortalCryptoBundle,
  PortalMarketsNewsItem,
  PortalResearchItem,
} from '@/lib/portal/marketsTypes'

export const PORTAL_DEFAULT_CRYPTO_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'SOLUSDT',
  'XRPUSDT',
  'BNBUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'USDCUSDT',
] as const

const SYMBOL_NAMES: Record<string, string> = {
  BTC: 'Bitcoin',
  ETH: 'Ether',
  SOL: 'Solana',
  XRP: 'XRP',
  BNB: 'BNB',
  ADA: 'Cardano',
  DOGE: 'Dogecoin',
  USDC: 'USD Coin',
  USDT: 'Tether',
}

function tickerFromSymbol(symbol: string): string {
  const upper = symbol.trim().toUpperCase()
  if (upper.endsWith('USDT')) return upper.slice(0, -4)
  if (upper.endsWith('USDC')) return upper.slice(0, -4)
  return upper
}

function nameFromSymbol(symbol: string): string {
  const ticker = tickerFromSymbol(symbol)
  return SYMBOL_NAMES[ticker] ?? ticker
}

export function formatCryptoPrice(value: number, currency: 'EUR' | 'USD' = 'USD'): string {
  const abs = Math.abs(value)
  const fractionDigits = abs >= 1 ? 2 : abs >= 0.01 ? 4 : 6
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency === 'EUR' ? 'EUR' : 'USD',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value)
}

export function formatChangePct(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

/** Variation 24h pour `AppAccountSummaryRow` (flèche DS + valeur absolue, locale fr). */
export function formatChangePctIndicator(value: number): string {
  return `${new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(Math.abs(value))}\u00a0%`
}

type MarketSummaryRow = {
  symbol?: string
  price?: number | string | null
  price_eur?: number | string | null
  priceEur?: number | string | null
  change_24h_pct?: number | string | null
  change24h_pct?: number | string | null
  change24hPct?: number | string | null
  logo_url?: string | null
  logoUrl?: string | null
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

export function mapMarketSummaryRow(
  row: MarketSummaryRow,
  options?: { currency?: 'EUR' | 'USD'; logoBaseUrl?: string },
): PortalCryptoAsset {
  const currency = options?.currency ?? 'USD'
  const symbol = (row.symbol ?? '').trim().toUpperCase()
  const ticker = tickerFromSymbol(symbol)
  const eur = toNumber(row.price_eur ?? row.priceEur, NaN)
  const usd = toNumber(row.price, NaN)
  const priceUsd = !Number.isNaN(usd) ? usd : 0
  const price =
    currency === 'EUR' && !Number.isNaN(eur) ? eur : priceUsd

  const rawLogo = (row.logo_url ?? row.logoUrl)?.toString?.() ?? null

  return {
    id: symbol || ticker,
    name: nameFromSymbol(symbol),
    ticker,
    symbol,
    priceUsd,
    priceLabel: formatCryptoPrice(price, currency),
    changePct: toNumber(row.change_24h_pct ?? row.change24h_pct ?? row.change24hPct),
    logoUrl: rawLogo,
  }
}

export function mapMarketSummaryList(
  rows: unknown,
  options?: { currency?: 'EUR' | 'USD'; logoBaseUrl?: string },
): PortalCryptoAsset[] {
  if (!Array.isArray(rows)) return []
  return rows
    .map((row) => mapMarketSummaryRow(row as MarketSummaryRow, options))
    .filter((row) => row.symbol)
}

type AllCryptoSummaryRow = MarketSummaryRow & {
  name?: string | null
  provider_symbol?: string | null
  market_cap_rank?: number | string | null
}

function mapAllCryptoSummaryRow(
  row: AllCryptoSummaryRow,
  options?: { currency?: 'EUR' | 'USD'; logoBaseUrl?: string },
): (PortalCryptoAsset & { marketCapRank: number }) | null {
  const providerSymbol = String(row.provider_symbol ?? row.symbol ?? '')
    .trim()
    .toUpperCase()
  const instrumentSymbol = String(row.symbol ?? '')
    .trim()
    .toUpperCase()
  const symbol = providerSymbol || instrumentSymbol
  if (!symbol) return null

  const ticker = instrumentSymbol || tickerFromSymbol(symbol)
  const mapped = mapMarketSummaryRow({ ...row, symbol }, options)
  const name = String(row.name ?? '').trim()
  const marketCapRank = toNumber(row.market_cap_rank, 9999)

  return {
    ...mapped,
    id: symbol,
    name: name || mapped.name,
    ticker,
    symbol,
    marketCapRank,
  }
}

/** Tous les instruments crypto actifs — tri market cap décroissant (aligné Flutter `AllCryptoApi`). */
export function mapAllCryptoList(
  rows: unknown,
  options?: { currency?: 'EUR' | 'USD'; logoBaseUrl?: string },
): PortalCryptoAsset[] {
  if (!Array.isArray(rows)) return []

  return rows
    .map((row) => mapAllCryptoSummaryRow(row as AllCryptoSummaryRow, options))
    .filter((item): item is PortalCryptoAsset & { marketCapRank: number } => item != null)
    .sort((a, b) => a.marketCapRank - b.marketCapRank)
    .map(({ marketCapRank: _rank, ...asset }) => asset)
}

type PortalFavoriteRow = {
  id?: string
  entity_type?: string
  entity_id?: string
}

/** entity_id API → ticker court (BTCUSDT → BTC). */
export function entityIdToTicker(entityId: string): string {
  const upper = entityId.trim().toUpperCase()
  if (upper.endsWith('USDT')) return upper.slice(0, -4)
  if (upper.endsWith('USDC')) return upper.slice(0, -4)
  return upper
}

function fallbackFavoriteAsset(entityId: string, currency: 'USD' | 'EUR' = 'USD'): PortalCryptoAsset {
  const symbol = entityId.trim().toUpperCase()
  const ticker = entityIdToTicker(symbol)
  return {
    id: symbol || ticker,
    name: nameFromSymbol(symbol || `${ticker}USDT`),
    ticker,
    symbol: symbol.includes('USDT') || symbol.includes('USDC') ? symbol : `${ticker}USDT`,
    priceUsd: 0,
    priceLabel: '—',
    changePct: 0,
    logoUrl: null,
  }
}

/** Favoris instrument + market-summary — aligné Flutter `_favoriteAssets`. */
export function mapFavoriteCryptoAssets(
  favorites: unknown,
  summaryRows: unknown,
  options?: { currency?: 'EUR' | 'USD'; logoBaseUrl?: string },
): PortalCryptoAsset[] {
  if (!Array.isArray(favorites)) return []
  const currency = options?.currency ?? 'USD'
  const instrumentFavorites = favorites.filter((raw) => {
    const row = raw as PortalFavoriteRow
    return row.entity_type === 'instrument' && row.entity_id?.trim()
  }) as PortalFavoriteRow[]

  if (instrumentFavorites.length === 0) return []

  const summaries = mapMarketSummaryList(summaryRows, options)
  if (summaries.length > 0) {
    const bySymbol = new Map(summaries.map((asset) => [asset.symbol.toUpperCase(), asset]))
    return instrumentFavorites.map((fav) => {
      const entityId = fav.entity_id!.trim().toUpperCase()
      return bySymbol.get(entityId) ?? fallbackFavoriteAsset(entityId, currency)
    })
  }

  return instrumentFavorites.map((fav) => fallbackFavoriteAsset(fav.entity_id!, currency))
}

/** Applique les mises à jour WS sur une liste d’assets (onglet actif). */
export function applyQuoteUpdates(
  assets: PortalCryptoAsset[],
  updates: MarketQuoteUpdate[],
  currency: 'USD' | 'EUR' = 'USD',
): PortalCryptoAsset[] {
  if (updates.length === 0) return assets
  const bySymbol = new Map(updates.map((u) => [u.symbol.toUpperCase(), u]))
  let changed = false

  const next = assets.map((asset) => {
    const update = bySymbol.get(asset.symbol.toUpperCase())
    if (!update || update.price <= 0) return asset
    changed = true
    return {
      ...asset,
      priceUsd: update.price,
      priceLabel: formatCryptoPrice(update.price, currency),
    }
  })

  return changed ? next : assets
}

type BundleCatalogItem = {
  id?: string
  product_code?: string
  productCode?: string
  name?: string
  description?: string | null
  risk_label?: string | null
  riskLabel?: string | null
  portfolio_id?: string | null
  portfolioId?: string | null
  entry_asset_default?: string | null
  entryAssetDefault?: string | null
  entry_assets_allowed?: string[] | null
  entryAssetsAllowed?: string[] | null
}

type BundleConfig = {
  headerMediaUrl?: string | null
  cardTitle?: string | null
  performance1d?: number | null
}

export function mapCryptoBundles(
  catalogItems: unknown,
  configs: Record<string, BundleConfig>,
): PortalCryptoBundle[] {
  if (!Array.isArray(catalogItems)) return []

  return catalogItems
    .map((raw) => {
      const item = raw as BundleCatalogItem
      const code = (item.product_code ?? item.productCode ?? '').trim().toUpperCase()
      if (!code) return null
      const config = configs[code] ?? configs[code.toLowerCase()]
      const entryAllowedRaw = item.entry_assets_allowed ?? item.entryAssetsAllowed
      const entryAssetsAllowed = Array.isArray(entryAllowedRaw)
        ? entryAllowedRaw.map((a) => String(a).trim().toUpperCase()).filter(Boolean)
        : []

      return {
        id: item.id?.trim() || code,
        code,
        title: config?.cardTitle?.trim() || item.name?.trim() || code,
        description: item.description?.trim() || '',
        imageUrl: config?.headerMediaUrl ?? null,
        performance1d: config?.performance1d ?? null,
        riskLabel: (item.risk_label ?? item.riskLabel)?.toString?.() ?? null,
        portfolioId: (item.portfolio_id ?? item.portfolioId)?.trim() || null,
        productId: item.id?.trim() || null,
        entryAssetDefault:
          (item.entry_asset_default ?? item.entryAssetDefault)?.trim().toUpperCase() || null,
        entryAssetsAllowed,
      } satisfies PortalCryptoBundle
    })
    .filter((item): item is PortalCryptoBundle => item != null)
    .sort((a, b) => a.title.localeCompare(b.title))
}

function resolveNewsTagLabel(
  slug: string,
  articleCategories: Array<{ slug: string; label: string }>,
  categories: Array<{ slug: string; label: string }>,
): string {
  const normalized = slug.trim()
  if (!normalized) return ''
  const articleCategory = articleCategories.find((cat) => cat.slug === normalized)
  if (articleCategory?.label?.trim()) return articleCategory.label.trim()
  const category = categories.find((cat) => cat.slug === normalized)
  if (category?.label?.trim()) return category.label.trim()
  return normalized
}

function newsTagsFromSlugs(
  categorySlugs: unknown,
  articleCategories: Array<{ slug: string; label: string }>,
  categories: Array<{ slug: string; label: string }>,
): string[] {
  const slugs = Array.isArray(categorySlugs)
    ? categorySlugs.map((tag) => String(tag)).filter(Boolean)
    : []
  return [...new Set(slugs.map((slug) => resolveNewsTagLabel(slug, articleCategories, categories)).filter(Boolean))]
}

function mapMarketsNewsRow(
  raw: unknown,
  options?: {
    articleCategories?: Array<{ slug: string; label: string }>
    categories?: Array<{ slug: string; label: string }>
    origin?: string
  },
): PortalMarketsNewsItem | null {
  const row = raw as Record<string, unknown>
  const slug = String(row.slug ?? '').trim()
  const id = String(row.id ?? slug).trim()
  if (!id) return null
  const articleCategories = options?.articleCategories ?? []
  const categories = options?.categories ?? []
  const hrefPath = slug ? `/blog/${encodeURIComponent(slug)}` : '/blog'
  const href =
    options?.origin && !hrefPath.startsWith('http')
      ? `${options.origin}${hrefPath}`
      : hrefPath
  return {
    id,
    slug,
    title: String(row.title ?? '').trim() || 'News',
    coverUrl: String(row.coverUrl ?? row.cover_url ?? '').trim(),
    authorName: String(row.authorName ?? row.author_name ?? 'Vancelian').trim(),
    publishedAt: typeof row.publishedAt === 'string' ? row.publishedAt : typeof row.published_at === 'string' ? row.published_at : null,
    readingTime: toNumber(row.readingTime ?? row.reading_time, 3),
    href,
    tags: newsTagsFromSlugs(row.categorySlugs ?? row.category_slugs, articleCategories, categories),
  }
}

export function mapMarketsNews(items: unknown): PortalMarketsNewsItem[] {
  if (!Array.isArray(items)) return []
  return items
    .map((raw) => mapMarketsNewsRow(raw))
    .filter((item): item is PortalMarketsNewsItem => item != null)
}

/** Feed blog Markets — aligné Flutter `_loadLatestNews` (featured + highlighted + articles, dédup, NEWS). */
export function mapMarketsNewsFeed(
  payload: unknown,
  options?: { maxItems?: number; origin?: string },
): PortalMarketsNewsItem[] {
  const root = payload as Record<string, unknown> | null
  if (!root) return []

  const articleCategories = Array.isArray(root.articleCategories)
    ? (root.articleCategories as Array<{ slug: string; label: string }>)
    : []
  const categories = Array.isArray(root.categories)
    ? (root.categories as Array<{ slug: string; label: string }>)
    : []

  const ordered: unknown[] = []
  if (root.featured) ordered.push(root.featured)
  if (Array.isArray(root.highlighted)) ordered.push(...root.highlighted)
  if (Array.isArray(root.articles)) ordered.push(...root.articles)

  const byId = new Map<string, PortalMarketsNewsItem>()
  for (const raw of ordered) {
    const row = raw as Record<string, unknown>
    const articleType = String(row.articleType ?? row.article_type ?? 'NEWS').toUpperCase()
    if (articleType !== 'NEWS') continue
    const mapped = mapMarketsNewsRow(raw, { articleCategories, categories, origin: options?.origin })
    if (!mapped || byId.has(mapped.id)) continue
    byId.set(mapped.id, mapped)
  }

  const maxItems = Math.min(Math.max(options?.maxItems ?? 5, 1), 10)
  return [...byId.values()].slice(0, maxItems)
}

/** Items widget Builder (blog-a-la-une, top10news…) → liste portail. */
export function mapWidgetNewsItems(feed: unknown, origin?: string): PortalMarketsNewsItem[] {
  const items = (feed as { items?: unknown })?.items
  if (!Array.isArray(items)) return []

  const mappedItems: PortalMarketsNewsItem[] = []
  for (const raw of items) {
    const row = raw as Record<string, unknown>
    const categoryLabels = Array.isArray(row.categoryLabels)
      ? row.categoryLabels.map((label) => String(label).trim()).filter(Boolean)
      : []
    const mapped = mapMarketsNewsRow(
      {
        id: row.id,
        slug: row.slug,
        title: row.title,
        coverUrl: row.coverUrl ?? row.cover_url,
        authorName: row.authorName ?? row.author_name ?? 'Vancelian',
        publishedAt: row.publishedAt ?? row.published_at,
        readingTime: row.readingTime ?? row.reading_time,
        categorySlugs: row.categorySlugs ?? (row.categorySlug ? [row.categorySlug] : []),
      },
      undefined,
    )
    if (!mapped) continue
    const hrefPath = mapped.slug ? `/blog/${encodeURIComponent(mapped.slug)}` : '/blog'
    const href =
      hrefPath.startsWith('http') || !origin ? hrefPath : `${origin}${hrefPath}`
    mappedItems.push({
      ...mapped,
      tags: mapped.tags.length > 0 ? mapped.tags : categoryLabels,
      href,
    })
  }
  return mappedItems
}

/** Feed widget research-a-la-une (filtré asset) → grille portail. */
export function mapWidgetResearchItems(feed: unknown, origin?: string): PortalResearchItem[] {
  const items = (feed as { items?: unknown })?.items
  if (!Array.isArray(items)) return []

  const mapped: PortalResearchItem[] = []
  for (const raw of items) {
    const row = raw as Record<string, unknown>
    const slug = String(row.slug ?? '').trim()
    const title = String(row.title ?? '').trim()
    if (!title) continue
    const hrefPath = slug ? `/blog/${encodeURIComponent(slug)}` : '/blog'
    const href =
      hrefPath.startsWith('http') || !origin ? hrefPath : `${origin}${hrefPath}`
    mapped.push({
      id: String(row.id ?? slug ?? title),
      title,
      coverUrl: String(row.coverUrl ?? row.cover_url ?? '').trim(),
      readingTime: toNumber(row.readingTime ?? row.reading_time, 5),
      tag: String(row.categoryLabel ?? row.categorySlug ?? '').trim() || undefined,
      href,
    })
  }
  return mapped
}

export function mapResearchWidget(payload: unknown): PortalResearchItem[] {
  const root = payload as Record<string, unknown> | null
  const feeds = root?.feeds as Record<string, unknown> | undefined
  if (!feeds) return []

  const items: PortalResearchItem[] = []
  for (const feed of Object.values(feeds)) {
    const feedObj = feed as Record<string, unknown>
    const cards = Array.isArray(feedObj.items) ? feedObj.items : []
    for (const card of cards) {
      const row = card as Record<string, unknown>
      const title = String(row.title ?? '').trim()
      const slug = String(row.slug ?? '').trim()
      if (!title) continue
      items.push({
        id: String(row.id ?? slug ?? title),
        title,
        coverUrl: String(row.coverUrl ?? row.cover_url ?? '').trim(),
        readingTime: toNumber(row.readingTime ?? row.reading_time, 5),
        tag: String(row.categoryLabel ?? row.categorySlug ?? '').trim() || undefined,
        href: slug ? `/blog/${encodeURIComponent(slug)}` : '/blog',
      })
    }
  }
  return items.slice(0, 10)
}
