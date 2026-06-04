import { normalizeNavPath } from '@/components/site/NavPendingContext'
import { PORTAL_MAIN_NAV_TABS } from '@/lib/portal/portalNavModel'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Onglets principaux + profil + wallet — prefetch idle (G4-B1.5), pas les pages profondes. */
export const PORTAL_MAIN_NAV_PREFETCH_ROUTES = [
  ...PORTAL_MAIN_NAV_TABS.map((tab) => tab.href),
  PORTAL_ROUTES.profile,
  PORTAL_ROUTES.cryptoWallet,
] as const

/** @deprecated Utiliser {@link PORTAL_MAIN_NAV_PREFETCH_ROUTES}. */
export const PORTAL_IDLE_WARMUP_ROUTES = PORTAL_MAIN_NAV_PREFETCH_ROUTES

type PortalRouter = { prefetch: (href: string) => void }

/** Prefetch Next.js route on hover/focus — sans warmup API automatique. */
export function warmPortalRoute(href: string, router?: PortalRouter): void {
  const route = normalizeNavPath(href)
  router?.prefetch(route)
}

/** Prefetch des routes shell principales (requestIdleCallback depuis la topnav). */
export function prefetchPortalMainNavRoutes(router: PortalRouter): void {
  for (const href of PORTAL_MAIN_NAV_PREFETCH_ROUTES) {
    router.prefetch(href)
  }
}

export function schedulePortalMainNavPrefetch(router: PortalRouter): () => void {
  const run = () => prefetchPortalMainNavRoutes(router)
  if (typeof requestIdleCallback !== 'undefined') {
    const id = requestIdleCallback(run, { timeout: 2500 })
    return () => cancelIdleCallback(id)
  }
  const timer = window.setTimeout(run, 80)
  return () => window.clearTimeout(timer)
}

/** @deprecated Idle warmup depuis PortalShell interdit (perf guard) — utiliser schedulePortalMainNavPrefetch dans la topnav. */
export function warmAllPortalMainRoutes(router: PortalRouter): void {
  prefetchPortalMainNavRoutes(router)
}
