import { readPortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_SECTION_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import type {
  PortalMarketsBundlesPayload,
  PortalMarketsDiscoverPayload,
  PortalMarketsPayload,
  PortalMarketsTopPayload,
} from '@/lib/portal/marketsTypes'

/**
 * Reconstruit un payload markets composite depuis les caches de section
 * (top + bundles + discover) pour la preview de navigation stale-while-navigate.
 * Retourne null tant que la section « top » n'est pas en cache.
 */
export function readPortalMarketsPayloadFromCache(): PortalMarketsPayload | null {
  const top = readPortalCache<PortalMarketsTopPayload>(PORTAL_SECTION_CACHE_KEYS.marketsTop)
  if (!top) return null

  const bundles = readPortalCache<PortalMarketsBundlesPayload>(
    PORTAL_SECTION_CACHE_KEYS.marketsBundles,
  )
  const discover = readPortalCache<PortalMarketsDiscoverPayload>(
    PORTAL_SECTION_CACHE_KEYS.marketsDiscover,
  )

  return {
    popular: top.popular,
    topGainers: top.topGainers,
    topLosers: top.topLosers,
    favorites: top.favorites,
    allCrypto: [],
    bundles: bundles?.bundles ?? [],
    news: discover?.news ?? [],
    research: discover?.research ?? [],
    marketDataPublicBaseUrl: top.marketDataPublicBaseUrl,
    currency: 'USD',
    partial: top.partial,
  }
}
