import { buildBackendUrl } from '@/lib/backend'
import { resolveDashboardCryptoSummary } from '@/lib/portal/dashboardFormat'
import { resolveDashboardReferenceCurrency } from '@/lib/portal/dashboardMerge'
import type {
  PortalDashboardBootstrap,
  PortalDashboardCash,
  PortalDashboardCorePayload,
  PortalDashboardPortfolioPayload,
  PortalDashboardProfile,
  PortalGlobalHistoryPoint,
  PortalGlobalStatistics,
  PortalPlacementsSummary,
  PortalPrivyPersonWallets,
} from '@/lib/portal/dashboardTypes'
import { loadPortalSavingsSummary } from '@/lib/portal/portalSavingsService'
import { assetToMarketProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'

export async function fetchPortalUpstreamJson(path: string) {
  const res = await portalUpstreamFetch(path, { signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

export async function fetchPortalBackendJson(path: string) {
  const res = await fetch(buildBackendUrl(path), {
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

/** Données rapides — header, comptes EUR, bannière inscription (sans CMS ni crypto lourd). */
export async function loadPortalDashboardCorePayload(): Promise<PortalDashboardCorePayload> {
  const [bootstrap, profile, cash, globalStatistics, globalHistory, notifications, privyPersonWallets] =
    await Promise.all([
      fetchPortalUpstreamJson('/api/app/bootstrap'),
      fetchPortalUpstreamJson('/api/app/profile'),
      fetchPortalUpstreamJson('/api/app/cash'),
      fetchPortalUpstreamJson('/api/app/portfolio/global/statistics'),
      fetchPortalUpstreamJson('/api/app/portfolio/global/history?period=ALL'),
      fetchPortalUpstreamJson('/api/app/notifications/unread-count'),
      fetchPortalUpstreamJson('/auth/privy/person-wallets'),
    ])

  const partial =
    !bootstrap.ok ||
    !profile.ok ||
    !cash.ok ||
    !globalStatistics.ok ||
    !globalHistory.ok

  return {
    bootstrap: (bootstrap.ok ? bootstrap.data : null) as PortalDashboardBootstrap,
    profile: (profile.ok ? profile.data : null) as PortalDashboardProfile,
    cash: (cash.ok ? cash.data : null) as PortalDashboardCash,
    globalStatistics: (globalStatistics.ok ? globalStatistics.data : null) as PortalGlobalStatistics,
    globalHistory: (globalHistory.ok
      ? globalHistory.data
      : null) as { points?: PortalGlobalHistoryPoint[] } | null,
    notifications: notifications.ok
      ? (notifications.data as { count?: number } | null)
      : null,
    privyPersonWallets: (privyPersonWallets.ok
      ? privyPersonWallets.data
      : null) as PortalPrivyPersonWallets,
    partial,
  }
}

/** Positions crypto + placements + épargne DeFi — chargé après le core (aligné mobile). */
export async function loadPortalDashboardPortfolioPayload(
  personId: string,
  options?: { currencyHint?: string; walletAddress?: string | null },
): Promise<PortalDashboardPortfolioPayload> {
  const currencyHint = options?.currencyHint
  const walletAddress = options?.walletAddress?.trim() || undefined

  const [bootstrap, cryptoPositions, privyBalances, placements, savingsResult] = await Promise.all([
    currencyHint ? Promise.resolve({ ok: true, data: null }) : fetchPortalUpstreamJson('/api/app/bootstrap'),
    fetchPortalUpstreamJson('/api/app/crypto-positions'),
    fetchPortalUpstreamJson('/api/app/privy-wallet/balances'),
    fetchPortalUpstreamJson('/api/app/lending/earn/positions'),
    loadPortalSavingsSummary({ personId, live: true, walletAddress }),
  ])

  const currency =
    currencyHint?.trim().toUpperCase() ||
    resolveDashboardReferenceCurrency(bootstrap.ok ? bootstrap.data : null)

  const privyList = Array.isArray(
    (privyBalances.data as { balances?: unknown } | null)?.balances,
  )
    ? ((privyBalances.data as { balances: { asset?: string }[] }).balances ?? [])
    : []
  const symbols = [...new Set(privyList.map((b) => assetToMarketProviderSymbol(String(b.asset ?? ''))))]
    .filter(Boolean)
    .join(',')

  const marketRes =
    symbols.length > 0
      ? await fetchPortalBackendJson(
          `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
        )
      : { ok: false, data: null }

  const crypto = resolveDashboardCryptoSummary(
    cryptoPositions.ok ? cryptoPositions.data : null,
    privyBalances.ok ? privyBalances.data : null,
    marketRes.ok ? marketRes.data : null,
    currency,
  )

  const partial = !cryptoPositions.ok || !privyBalances.ok || !placements.ok || savingsResult.partial

  return {
    crypto,
    placements: (placements.ok ? placements.data : null) as PortalPlacementsSummary,
    savings: savingsResult.savings,
    partial,
  }
}
