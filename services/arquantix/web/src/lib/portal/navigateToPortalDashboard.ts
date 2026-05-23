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
  void revalidatePortalCache<unknown>(
    DASHBOARD_CACHE_KEY,
    DASHBOARD_API_URL,
    DASHBOARD_CACHE_TTL_MS,
  ).catch(() => {
    /* le dashboard re-fetchera au montage si le warm-up échoue */
  })

  // Navigation pleine page : garantit l’envoi des cookies httpOnly posés par /privy/exchange
  // (router.replace SPA peut arriver avant que le jar soit visible côté middleware).
  if (typeof window !== 'undefined') {
    window.location.assign(PORTAL_ROUTES.dashboard)
    return
  }

  router.replace(PORTAL_ROUTES.dashboard)
}
