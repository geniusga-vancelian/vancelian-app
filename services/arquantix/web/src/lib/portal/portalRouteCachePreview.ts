import { normalizeNavPath } from '@/components/site/NavPendingContext'
import { PORTAL_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { readPortalDashboardPayloadFromCache } from '@/lib/portal/dashboardCache'
import { readPortalCache } from '@/lib/portal/portalClientCache'
import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import { PORTAL_PATH_PREFIX, PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export type PortalRouteCachedPayload =
  | { kind: 'dashboard'; data: PortalDashboardPayload }
  | { kind: 'markets'; data: PortalMarketsPayload }
  | { kind: 'invest'; data: PortalInvestPayload }
  | { kind: 'profile'; data: { profile: PortalDashboardPayload['profile'] } }
  | { kind: 'crypto-wallet'; data: PortalCryptoWalletHubPayload }

export function readPortalRouteCachedPayload(route: string): PortalRouteCachedPayload | null {
  const normalized = normalizeNavPath(route)

  if (normalized === PORTAL_ROUTES.dashboard || normalized === PORTAL_PATH_PREFIX) {
    const data = readPortalDashboardPayloadFromCache()
    return data ? { kind: 'dashboard', data } : null
  }

  if (normalized === PORTAL_ROUTES.markets) {
    const data = readPortalCache<PortalMarketsPayload>(PORTAL_CACHE_KEYS.markets)
    return data ? { kind: 'markets', data } : null
  }

  if (normalized === PORTAL_ROUTES.invest) {
    const data = readPortalCache<PortalInvestPayload>(PORTAL_CACHE_KEYS.invest)
    return data ? { kind: 'invest', data } : null
  }

  if (normalized === PORTAL_ROUTES.profile) {
    const data = readPortalCache<{ profile: PortalDashboardPayload['profile'] }>(
      PORTAL_CACHE_KEYS.profile,
    )
    return data ? { kind: 'profile', data } : null
  }

  if (normalized === PORTAL_ROUTES.cryptoWallet) {
    const data = readPortalCache<PortalCryptoWalletHubPayload>(PORTAL_CACHE_KEYS.cryptoWallet)
    return data ? { kind: 'crypto-wallet', data } : null
  }

  return null
}

export function hasPortalRouteCachedPreview(route: string): boolean {
  return readPortalRouteCachedPayload(route) !== null
}
