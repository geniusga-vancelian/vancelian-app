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
  PortalSavingsSummary,
} from '@/lib/portal/dashboardTypes'
import { loadPortalSavingsSummary } from '@/lib/portal/portalSavingsService'
import { assetToMarketProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import {
  fetchPortalBackendJsonSafe,
  fetchPortalUpstreamJsonSafe,
  PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
} from '@/lib/portal/portalUpstream'

export async function fetchPortalUpstreamJson(
  path: string,
  options?: { timeoutMs?: number },
) {
  return fetchPortalUpstreamJsonSafe(path, options)
}

export async function fetchPortalBackendJson(
  path: string,
  options?: { timeoutMs?: number },
) {
  return fetchPortalBackendJsonSafe(path, options)
}

const EMPTY_SAVINGS_SUMMARY: PortalSavingsSummary = {
  positions_count: 0,
  positions: [],
  total_value_eur: 0,
  total_value_usd: 0,
}

async function loadPortalSavingsSummarySafe(args: {
  personId: string
  live?: boolean
  walletAddress?: string | null
}) {
  try {
    return await loadPortalSavingsSummary(args)
  } catch {
    return { savings: EMPTY_SAVINGS_SUMMARY, partial: true }
  }
}

/** Données rapides — header, comptes EUR, bannière inscription (sans CMS ni crypto lourd). */
export async function loadPortalDashboardCorePayload(): Promise<PortalDashboardCorePayload> {
  const [bootstrap, profile, cash, globalStatistics, globalHistory, notifications, privyPersonWallets] =
    await Promise.all([
      fetchPortalUpstreamJson('/api/app/bootstrap'),
      fetchPortalUpstreamJson('/api/app/profile'),
      fetchPortalUpstreamJson('/api/app/cash'),
      fetchPortalUpstreamJson('/api/app/portfolio/global/statistics', {
        timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
      }),
      fetchPortalUpstreamJson('/api/app/portfolio/global/history?period=ALL', {
        timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
      }),
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
    currencyHint
      ? Promise.resolve({ ok: true, data: null })
      : fetchPortalUpstreamJson('/api/app/bootstrap'),
    fetchPortalUpstreamJson('/api/app/crypto-positions/direct', {
      timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
    }),
    fetchPortalUpstreamJson('/api/app/privy-wallet/balances', {
      timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
    }),
    fetchPortalUpstreamJson('/api/app/lending/earn/positions'),
    loadPortalSavingsSummarySafe({ personId, live: true, walletAddress }),
  ])

  const currency =
    currencyHint?.trim().toUpperCase() ||
    resolveDashboardReferenceCurrency(bootstrap.ok ? bootstrap.data : null)

  const directList = Array.isArray(
    (cryptoPositions.data as { positions?: unknown } | null)?.positions,
  )
    ? ((cryptoPositions.data as { positions: { asset?: string }[] }).positions ?? [])
    : []
  const symbols = [...new Set(directList.map((p) => assetToMarketProviderSymbol(String(p.asset ?? ''))))]
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
    !cryptoPositions.ok && privyBalances.ok ? privyBalances.data : null,
    marketRes.ok ? marketRes.data : null,
    currency,
  )

  const partial = !cryptoPositions.ok || !placements.ok || savingsResult.partial

  return {
    crypto,
    placements: (placements.ok ? placements.data : null) as PortalPlacementsSummary,
    savings: savingsResult.savings,
    partial,
  }
}
