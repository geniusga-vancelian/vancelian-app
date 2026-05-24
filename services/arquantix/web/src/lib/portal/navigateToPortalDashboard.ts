import {
  DASHBOARD_CORE_API_URL,
  DASHBOARD_CORE_CACHE_KEY,
  DASHBOARD_CORE_TTL_MS,
  DASHBOARD_PORTFOLIO_API_URL,
  DASHBOARD_PORTFOLIO_CACHE_KEY,
  DASHBOARD_PORTFOLIO_TTL_MS,
  syncPortalDashboardCompositeCache,
} from '@/lib/portal/dashboardCache'
import type {
  PortalDashboardCorePayload,
  PortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardTypes'
import { revalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type PortalDashboardRouter = {
  replace: (href: string) => void
}

/**
 * Navigation post-login : précharge core + portfolio (progressif) avant redirect.
 */
export async function navigateToPortalDashboard(router: PortalDashboardRouter): Promise<void> {
  void Promise.all([
    revalidatePortalCache<PortalDashboardCorePayload>(
      DASHBOARD_CORE_CACHE_KEY,
      DASHBOARD_CORE_API_URL,
      DASHBOARD_CORE_TTL_MS,
    ),
    revalidatePortalCache<PortalDashboardPortfolioPayload>(
      DASHBOARD_PORTFOLIO_CACHE_KEY,
      DASHBOARD_PORTFOLIO_API_URL,
      DASHBOARD_PORTFOLIO_TTL_MS,
    ),
  ])
    .then(([core, portfolio]) => {
      syncPortalDashboardCompositeCache(core, portfolio)
    })
    .catch(() => {
      /* le dashboard re-fetchera au montage si le warm-up échoue */
    })

  if (typeof window !== 'undefined') {
    window.location.assign(PORTAL_ROUTES.dashboard)
    return
  }

  router.replace(PORTAL_ROUTES.dashboard)
}
