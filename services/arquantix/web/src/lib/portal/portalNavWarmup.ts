import { normalizeNavPath } from '@/components/site/NavPendingContext'
import { revalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type WarmupConfig = {
  cacheKey: string
  url: string
  ttlMs: number
}

const WARMUP_BY_ROUTE: Record<string, WarmupConfig> = {
  [PORTAL_ROUTES.dashboard]: {
    cacheKey: 'portal:dashboard',
    url: '/api/portal/dashboard?locale=fr',
    ttlMs: 60_000,
  },
  [PORTAL_ROUTES.invest]: {
    cacheKey: 'portal:invest:v2',
    url: '/api/portal/invest?locale=fr',
    ttlMs: 120_000,
  },
  [PORTAL_ROUTES.markets]: {
    cacheKey: 'portal:markets:v2',
    url: '/api/portal/markets?locale=fr',
    ttlMs: 60_000,
  },
  [PORTAL_ROUTES.profile]: {
    cacheKey: 'portal:profile',
    url: '/api/portal/profile',
    ttlMs: 120_000,
  },
}

export const PORTAL_IDLE_WARMUP_ROUTES = [
  PORTAL_ROUTES.dashboard,
  PORTAL_ROUTES.invest,
  PORTAL_ROUTES.markets,
  PORTAL_ROUTES.profile,
] as const

type PortalRouter = { prefetch: (href: string) => void }

/** Prefetch Next.js + warm cache API pour une route portail. */
export function warmPortalRoute(href: string, router?: PortalRouter): void {
  const route = normalizeNavPath(href)
  router?.prefetch(route)

  const config = WARMUP_BY_ROUTE[route]
  if (!config) return

  void revalidatePortalCache(config.cacheKey, config.url, config.ttlMs).catch(() => {})
}

/** Précharge les onglets principaux en idle (post-mount shell). */
export function warmAllPortalMainRoutes(router: PortalRouter): void {
  for (const href of PORTAL_IDLE_WARMUP_ROUTES) {
    warmPortalRoute(href, router)
  }
}
