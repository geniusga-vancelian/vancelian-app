import {
  mergePortalDashboardPayload,
  resolveDashboardReferenceCurrency,
} from '@/lib/portal/dashboardMerge'
import type {
  PortalDashboardCorePayload,
  PortalDashboardPayload,
  PortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardTypes'
import {
  getPortalCacheBootstrap,
  readPortalCache,
  writePortalCache,
} from '@/lib/portal/portalClientCache'

export const DASHBOARD_CACHE_KEY = 'portal:dashboard'
export const DASHBOARD_CORE_CACHE_KEY = 'portal:dashboard:core'
export const DASHBOARD_PORTFOLIO_CACHE_KEY = 'portal:dashboard:portfolio'

export const DASHBOARD_CORE_TTL_MS = 60_000
export const DASHBOARD_PORTFOLIO_TTL_MS = 45_000
export const DASHBOARD_COMPOSITE_TTL_MS = 60_000

export const DASHBOARD_CORE_API_URL = '/api/portal/dashboard/core'
export const DASHBOARD_PORTFOLIO_API_URL = '/api/portal/dashboard/portfolio'

export function syncPortalDashboardCompositeCache(
  core: PortalDashboardCorePayload | null | undefined,
  portfolio: PortalDashboardPortfolioPayload | null | undefined,
): PortalDashboardPayload | null {
  const merged = mergePortalDashboardPayload(core, portfolio)
  if (merged) {
    writePortalCache(DASHBOARD_CACHE_KEY, merged, DASHBOARD_COMPOSITE_TTL_MS)
  }
  return merged
}

/** Lecture synchrone pour preview navigation — composite ou sections fusionnées. */
export function readPortalDashboardPayloadFromCache(): PortalDashboardPayload | null {
  const composite = readPortalCache<PortalDashboardPayload>(DASHBOARD_CACHE_KEY)
  if (composite) return composite

  const core = readPortalCache<PortalDashboardCorePayload>(DASHBOARD_CORE_CACHE_KEY)
  const portfolio = readPortalCache<PortalDashboardPortfolioPayload>(DASHBOARD_PORTFOLIO_CACHE_KEY)
  return mergePortalDashboardPayload(core, portfolio)
}

export function getPortalDashboardBootstrapFromCache(): {
  core: ReturnType<typeof getPortalCacheBootstrap<PortalDashboardCorePayload>>
  portfolio: ReturnType<typeof getPortalCacheBootstrap<PortalDashboardPortfolioPayload>>
  composite: PortalDashboardPayload | null
} {
  const core = getPortalCacheBootstrap<PortalDashboardCorePayload>(DASHBOARD_CORE_CACHE_KEY)
  const portfolio =
    getPortalCacheBootstrap<PortalDashboardPortfolioPayload>(DASHBOARD_PORTFOLIO_CACHE_KEY)
  const composite =
    readPortalCache<PortalDashboardPayload>(DASHBOARD_CACHE_KEY) ??
    mergePortalDashboardPayload(core.data, portfolio.data)

  return { core, portfolio, composite }
}

export function resolvePortfolioCurrencyFromCore(
  core: PortalDashboardCorePayload | null | undefined,
): string {
  return resolveDashboardReferenceCurrency(core?.bootstrap)
}
