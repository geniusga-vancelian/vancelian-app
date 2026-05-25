import { normalizeNavPath } from '@/components/site/NavPendingContext'
import type {
  PortalDashboardCorePayload,
  PortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardTypes'
import {
  DASHBOARD_CORE_API_URL,
  DASHBOARD_CORE_CACHE_KEY,
  DASHBOARD_CORE_TTL_MS,
  DASHBOARD_PORTFOLIO_API_URL,
  DASHBOARD_PORTFOLIO_CACHE_KEY,
  DASHBOARD_PORTFOLIO_TTL_MS,
  syncPortalDashboardCompositeCache,
} from '@/lib/portal/dashboardCache'
import { revalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_PATH_PREFIX, PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type WarmupConfig = {
  cacheKey: string
  url: string
  ttlMs: number
}

const WARMUP_BY_ROUTE: Record<string, WarmupConfig[]> = {
  [PORTAL_ROUTES.dashboard]: [
    {
      cacheKey: DASHBOARD_CORE_CACHE_KEY,
      url: DASHBOARD_CORE_API_URL,
      ttlMs: DASHBOARD_CORE_TTL_MS,
    },
    {
      cacheKey: DASHBOARD_PORTFOLIO_CACHE_KEY,
      url: DASHBOARD_PORTFOLIO_API_URL,
      ttlMs: DASHBOARD_PORTFOLIO_TTL_MS,
    },
  ],
  [PORTAL_ROUTES.cryptoWallet]: [
    {
      cacheKey: 'portal:crypto-wallet',
      url: '/api/portal/crypto-wallet',
      ttlMs: 45_000,
    },
  ],
  [PORTAL_ROUTES.invest]: [
    {
      cacheKey: 'portal:invest:v2',
      url: '/api/portal/invest?locale=en',
      ttlMs: 120_000,
    },
  ],
  [PORTAL_ROUTES.markets]: [
    {
      cacheKey: 'portal:markets:v2',
      url: '/api/portal/markets?locale=fr',
      ttlMs: 60_000,
    },
  ],
  [PORTAL_ROUTES.profile]: [
    {
      cacheKey: 'portal:profile',
      url: '/api/portal/profile',
      ttlMs: 120_000,
    },
    {
      cacheKey: 'portal:privy-person-wallets',
      url: '/api/portal/privy/person-wallets',
      ttlMs: 60_000,
    },
    {
      cacheKey: 'portal:wallets:solana',
      url: '/api/portal/wallets/solana',
      ttlMs: 60_000,
    },
  ],
  [PORTAL_ROUTES.walletDeposit]: [
    {
      cacheKey: 'portal:privy-person-wallets',
      url: '/api/portal/privy/person-wallets',
      ttlMs: 60_000,
    },
  ],
  [PORTAL_ROUTES.walletDepositSol]: [
    {
      cacheKey: 'portal:wallets:solana',
      url: '/api/portal/wallets/solana',
      ttlMs: 60_000,
    },
  ],
  [PORTAL_ROUTES.walletSwap]: [
    {
      cacheKey: 'portal:crypto-wallet',
      url: '/api/portal/crypto-wallet',
      ttlMs: 45_000,
    },
  ],
  [PORTAL_ROUTES.walletCreate]: [
    {
      cacheKey: 'portal:profile',
      url: '/api/portal/profile',
      ttlMs: 120_000,
    },
  ],
  [PORTAL_ROUTES.myWallets]: [
    {
      cacheKey: 'portal:privy-person-wallets',
      url: '/api/portal/privy/person-wallets',
      ttlMs: 60_000,
    },
    {
      cacheKey: 'portal:wallets:solana',
      url: '/api/portal/wallets/solana',
      ttlMs: 60_000,
    },
  ],
}

export const PORTAL_IDLE_WARMUP_ROUTES = [
  PORTAL_ROUTES.dashboard,
  PORTAL_ROUTES.cryptoWallet,
  PORTAL_ROUTES.invest,
  PORTAL_ROUTES.markets,
  PORTAL_ROUTES.profile,
] as const

type PortalRouter = { prefetch: (href: string) => void }

function resolveWarmupConfigs(route: string): WarmupConfig[] {
  if (route === PORTAL_ROUTES.dashboard || route === PORTAL_PATH_PREFIX) {
    return WARMUP_BY_ROUTE[PORTAL_ROUTES.dashboard] ?? []
  }

  const direct = WARMUP_BY_ROUTE[route]
  if (direct) return direct

  const cryptoAssetPrefix = `${PORTAL_ROUTES.cryptoWallet}/`
  if (route.startsWith(cryptoAssetPrefix)) {
    const ticker = decodeURIComponent(route.slice(cryptoAssetPrefix.length).split('/')[0] ?? '')
      .trim()
      .toUpperCase()
    if (!ticker) return []
    return [
      {
        cacheKey: `portal:crypto-wallet:${ticker}`,
        url: `/api/portal/crypto-wallet/${encodeURIComponent(ticker)}`,
        ttlMs: 45_000,
      },
    ]
  }

  const marketsAssetPrefix = `${PORTAL_ROUTES.markets}/`
  if (route.startsWith(marketsAssetPrefix)) {
    const slug = decodeURIComponent(route.slice(marketsAssetPrefix.length).split('/')[0] ?? '')
      .trim()
      .toLowerCase()
    if (!slug) return []
    return [
      {
        cacheKey: `portal:instrument:${slug}`,
        url: `/api/portal/instruments/${encodeURIComponent(slug)}`,
        ttlMs: 60_000,
      },
    ]
  }

  return []
}

async function warmDashboardCaches(): Promise<void> {
  const [coreResult, portfolioResult] = await Promise.allSettled([
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

  const core = coreResult.status === 'fulfilled' ? coreResult.value : null
  const portfolio = portfolioResult.status === 'fulfilled' ? portfolioResult.value : null
  if (core || portfolio) {
    syncPortalDashboardCompositeCache(core, portfolio)
  }
}

/** Prefetch Next.js + warm cache API pour une route portail. */
export function warmPortalRoute(href: string, router?: PortalRouter): void {
  const route = normalizeNavPath(href)
  router?.prefetch(route)

  if (route === PORTAL_ROUTES.dashboard || route === PORTAL_PATH_PREFIX) {
    void warmDashboardCaches().catch(() => {})
    return
  }

  const configs = resolveWarmupConfigs(route)
  for (const config of configs) {
    void revalidatePortalCache(config.cacheKey, config.url, config.ttlMs).catch(() => {})
  }
}

/** Précharge les onglets principaux en idle (post-mount shell). */
export function warmAllPortalMainRoutes(router: PortalRouter): void {
  for (const href of PORTAL_IDLE_WARMUP_ROUTES) {
    warmPortalRoute(href, router)
  }
}
