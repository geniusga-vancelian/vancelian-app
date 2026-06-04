import { normalizeNavPath } from '@/components/site/NavPendingContext'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export const PORTAL_IDLE_WARMUP_ROUTES = [
  PORTAL_ROUTES.dashboard,
  PORTAL_ROUTES.cryptoWallet,
  PORTAL_ROUTES.invest,
  PORTAL_ROUTES.markets,
  PORTAL_ROUTES.academy,
  PORTAL_ROUTES.profile,
] as const

type PortalRouter = { prefetch: (href: string) => void }

/** Prefetch Next.js route on hover/focus — sans warmup API automatique. */
export function warmPortalRoute(href: string, router?: PortalRouter): void {
  const route = normalizeNavPath(href)
  router?.prefetch(route)
}

/** @deprecated Idle warmup massif retiré (Phase 1 perf) — prefetch ciblé via {@link warmPortalRoute}. */
export function warmAllPortalMainRoutes(router: PortalRouter): void {
  for (const href of PORTAL_IDLE_WARMUP_ROUTES) {
    router.prefetch(href)
  }
}
