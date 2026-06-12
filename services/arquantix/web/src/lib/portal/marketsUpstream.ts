import { buildBackendUrl } from '@/lib/backend'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import { fetchPortalUpstreamJsonSafe } from '@/lib/portal/portalUpstream'
import {
  mapCryptoBundles,
  mapFavoriteCryptoAssets,
  mapMarketSummaryList,
  mapMarketsNewsFeed,
  mapResearchWidget,
  PORTAL_DEFAULT_CRYPTO_SYMBOLS,
} from '@/lib/portal/marketsFormat'
import type {
  PortalMarketsBundlesPayload,
  PortalMarketsDiscoverPayload,
  PortalMarketsTopPayload,
} from '@/lib/portal/marketsTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

/** Agrégation BFF — 15s provoquait des timeouts prod, on aligne sur 30s. */
export const PORTAL_MARKETS_FETCH_TIMEOUT_MS = 30_000

async function fetchJson(url: string, init?: RequestInit) {
  try {
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(PORTAL_MARKETS_FETCH_TIMEOUT_MS),
      ...init,
    })
    const data = await res.json().catch(() => null)
    return { ok: res.ok, data }
  } catch {
    return { ok: false, data: null }
  }
}

/** Top crypto : populaires + gainers/losers + favoris. Section rapide pilotant le WS. */
export async function loadPortalMarketsTop(): Promise<PortalMarketsTopPayload> {
  const symbols = PORTAL_DEFAULT_CRYPTO_SYMBOLS.join(',')
  const marketDataPublicBaseUrl = getMarketDataPublicBaseUrl()
  const mapOptions = { currency: 'USD' as const, logoBaseUrl: marketDataPublicBaseUrl }

  const [popularRes, moversRes, favoritesRes] = await Promise.all([
    fetchJson(
      buildBackendUrl(`/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`),
    ),
    fetchJson(
      buildBackendUrl(`/api/market-data/top-movers?limit=10&symbols=${encodeURIComponent(symbols)}`),
    ),
    fetchPortalUpstreamJsonSafe('/api/app/favorites?entity_type=instrument', {
      timeoutMs: PORTAL_MARKETS_FETCH_TIMEOUT_MS,
    }),
  ])

  const popular = mapMarketSummaryList(
    (popularRes.data as { summaries?: unknown })?.summaries ??
      (Array.isArray(popularRes.data) ? popularRes.data : (popularRes.data as { items?: unknown })?.items),
    mapOptions,
  )

  const movers = moversRes.data as {
    top_gainers?: unknown
    topGainers?: unknown
    top_losers?: unknown
    topLosers?: unknown
  } | null
  const topGainers = mapMarketSummaryList(movers?.top_gainers ?? movers?.topGainers, mapOptions)
  const topLosers = mapMarketSummaryList(movers?.top_losers ?? movers?.topLosers, mapOptions)

  const favoritesJson = favoritesRes.ok && Array.isArray(favoritesRes.data) ? favoritesRes.data : []
  const favoriteEntityIds = favoritesJson
    .map((f) => (f as { entity_id?: string }).entity_id?.trim().toUpperCase())
    .filter(Boolean)

  let favoriteSummaryRows: unknown = null
  if (favoriteEntityIds.length > 0) {
    const favoriteSummaryRes = await fetchJson(
      buildBackendUrl(
        `/api/market-data/market-summary?symbols=${encodeURIComponent(favoriteEntityIds.join(','))}`,
      ),
    )
    if (favoriteSummaryRes.ok) {
      favoriteSummaryRows =
        (favoriteSummaryRes.data as { summaries?: unknown })?.summaries ?? favoriteSummaryRes.data
    }
  }
  const favorites = mapFavoriteCryptoAssets(favoritesJson, favoriteSummaryRows, mapOptions)

  return {
    popular,
    topGainers,
    topLosers,
    favorites,
    marketDataPublicBaseUrl,
    currency: 'USD',
    partial: !popularRes.ok || !moversRes.ok,
  }
}

/** Paniers crypto (catalog + configs CMS). `bffOrigin` pour le loopback configs. */
export async function loadPortalMarketsBundles(bffOrigin: string): Promise<PortalMarketsBundlesPayload> {
  const [configsRes, bundleRes] = await Promise.all([
    fetchJson(`${bffOrigin}/api/mobile/flutter/portfolio-products/configs`),
    fetchPortalUpstreamJsonSafe('/api/app/bundle/catalog', {
      timeoutMs: PORTAL_MARKETS_FETCH_TIMEOUT_MS,
    }),
  ])

  const configs = ((configsRes.data as { configs?: Record<string, unknown> })?.configs ?? {}) as Record<
    string,
    {
      headerMediaUrl?: string | null
      cardTitle?: string | null
      performance1d?: number | null
      sortOrder?: number | null
    }
  >

  let bundles: PortalMarketsBundlesPayload['bundles'] = []
  if (bundleRes.ok && bundleRes.data) {
    const catalogItems =
      (bundleRes.data as { items?: unknown })?.items ??
      (bundleRes.data as { products?: unknown })?.products ??
      bundleRes.data
    bundles = mapCryptoBundles(catalogItems, configs)
  }

  return { bundles, partial: !bundleRes.ok }
}

/** Section éditoriale : actualités (blog) + analyses (widget research). */
export async function loadPortalMarketsDiscover(
  bffOrigin: string,
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalMarketsDiscoverPayload> {
  const [newsRes, researchRes] = await Promise.all([
    fetchJson(`${bffOrigin}/api/blog?articleType=NEWS&page=1&pageSize=5&locale=${locale}`),
    fetchJson(`${bffOrigin}/api/mobile/flutter/widgets/top10research?locale=${locale}`),
  ])

  return {
    news: mapMarketsNewsFeed(newsRes.data, { maxItems: 5 }),
    research: mapResearchWidget(researchRes.data),
    partial: !newsRes.ok,
  }
}
