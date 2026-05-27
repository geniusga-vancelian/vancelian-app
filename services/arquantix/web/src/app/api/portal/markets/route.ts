import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import { portalUpstreamFetch, resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import {
  mapCryptoBundles,
  mapFavoriteCryptoAssets,
  mapMarketSummaryList,
  mapMarketsNewsFeed,
  mapResearchWidget,
  PORTAL_DEFAULT_CRYPTO_SYMBOLS,
} from '@/lib/portal/marketsFormat'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'

async function fetchJson(url: string, init?: RequestInit) {
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(15000), ...init })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

export async function GET(request: NextRequest) {
  try {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const publicOrigin = request.nextUrl.origin
  const bffOrigin = resolvePortalBffOrigin(publicOrigin)
  const symbols = PORTAL_DEFAULT_CRYPTO_SYMBOLS.join(',')

  const [popularRes, moversRes, newsRes, configsRes, researchRes, bundleRes, favoritesRes] =
    await Promise.all([
      fetchJson(
        buildBackendUrl(`/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`),
      ),
      fetchJson(
        buildBackendUrl(
          `/api/market-data/top-movers?limit=10&symbols=${encodeURIComponent(symbols)}`,
        ),
      ),
      fetchJson(`${bffOrigin}/api/blog?articleType=NEWS&page=1&pageSize=5&locale=fr`),
      fetchJson(`${bffOrigin}/api/mobile/flutter/portfolio-products/configs`),
      fetchJson(`${bffOrigin}/api/mobile/flutter/widgets/top10research?locale=fr`),
      portalUpstreamFetch('/api/app/bundle/catalog'),
      portalUpstreamFetch('/api/app/favorites?entity_type=instrument'),
    ])

  const marketDataPublicBaseUrl = getMarketDataPublicBaseUrl()
  const mapOptions = { currency: 'USD' as const, logoBaseUrl: marketDataPublicBaseUrl }

  const popular = mapMarketSummaryList(
    (popularRes.data as { summaries?: unknown })?.summaries ??
      (Array.isArray(popularRes.data) ? popularRes.data : popularRes.data?.items),
    mapOptions,
  )

  const movers = moversRes.data as { top_gainers?: unknown; topGainers?: unknown; top_losers?: unknown; topLosers?: unknown } | null
  const topGainers = mapMarketSummaryList(movers?.top_gainers ?? movers?.topGainers, mapOptions)
  const topLosers = mapMarketSummaryList(movers?.top_losers ?? movers?.topLosers, mapOptions)

  const newsItems = mapMarketsNewsFeed(newsRes.data, { maxItems: 5, origin: publicOrigin })
  const configs = ((configsRes.data as { configs?: Record<string, unknown> })?.configs ?? {}) as Record<
    string,
    {
      headerMediaUrl?: string | null
      cardTitle?: string | null
      performance1d?: number | null
      sortOrder?: number | null
    }
  >

  let bundles: PortalMarketsPayload['bundles'] = []
  if (bundleRes.ok) {
    const bundleJson = await bundleRes.json().catch(() => null)
    const catalogItems =
      (bundleJson as { items?: unknown })?.items ??
      (bundleJson as { products?: unknown })?.products ??
      bundleJson
    bundles = mapCryptoBundles(catalogItems, configs)
  }

  const research = mapResearchWidget(researchRes.data)

  const favoritesJson = favoritesRes.ok ? await favoritesRes.json().catch(() => []) : []
  const favoriteEntityIds = Array.isArray(favoritesJson)
    ? favoritesJson
        .map((f) => (f as { entity_id?: string }).entity_id?.trim().toUpperCase())
        .filter(Boolean)
    : []

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

  const partial =
    !popularRes.ok ||
    !moversRes.ok ||
    !newsRes.ok ||
    bundles.length === 0

  const payload: PortalMarketsPayload = {
    popular,
    topGainers,
    topLosers,
    favorites,
    allCrypto: [],
    bundles,
    news: newsItems,
    research,
    marketDataPublicBaseUrl,
    currency: 'USD',
    partial,
  }

  return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/markets GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
