import { revalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const DASHBOARD_CACHE_KEY = 'portal:dashboard'
const DASHBOARD_API_URL = '/api/portal/dashboard?locale=fr'
const DASHBOARD_CACHE_TTL_MS = 60_000

type PortalDashboardRouter = {
  replace: (href: string) => void
}

/**
 * Navigation post-login sans `router.refresh()` :
 * précharge le dashboard en cache pour éviter le skeleton au premier paint.
 */
export async function navigateToPortalDashboard(router: PortalDashboardRouter): Promise<void> {
  try {
    await revalidatePortalCache<unknown>(
      DASHBOARD_CACHE_KEY,
      DASHBOARD_API_URL,
      DASHBOARD_CACHE_TTL_MS,
    )
  } catch {
    /* le dashboard re-fetchera au montage si le warm-up échoue */
  }

  router.replace(PORTAL_ROUTES.dashboard)
}
