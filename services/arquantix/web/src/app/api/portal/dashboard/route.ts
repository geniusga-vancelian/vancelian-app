import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { resolveDashboardCryptoSummary } from '@/lib/portal/dashboardFormat'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { loadPortalTop10NewsWidget } from '@/lib/portal/loadTop10NewsWidget'

async function fetchUpstreamJson(path: string) {
  const res = await portalUpstreamFetch(path, { signal: AbortSignal.timeout(15000) })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

async function fetchBackendJson(path: string) {
  const res = await fetch(buildBackendUrl(path), {
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })
  const data = await res.json().catch(() => null)
  return { ok: res.ok, data }
}

/** Agrège les données home Flutter pour le dashboard portail (cookie httpOnly). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
  const origin = request.nextUrl.origin

  const [
    bootstrap,
    profile,
    cash,
    globalStatistics,
    globalHistory,
    cryptoPositions,
    privyBalances,
    placements,
    notifications,
    newsWidget,
    privyPersonWallets,
  ] = await Promise.all([
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson('/api/app/profile'),
    fetchUpstreamJson('/api/app/cash'),
    fetchUpstreamJson('/api/app/portfolio/global/statistics'),
    fetchUpstreamJson('/api/app/portfolio/global/history?period=ALL'),
    fetchUpstreamJson('/api/app/crypto-positions'),
    fetchUpstreamJson('/api/app/privy-wallet/balances'),
    fetchUpstreamJson('/api/app/lending/earn/positions'),
    fetchUpstreamJson('/api/app/notifications/unread-count'),
    loadPortalTop10NewsWidget(locale, origin).catch(() => null),
    fetchUpstreamJson('/auth/privy/person-wallets'),
  ])

  const currency =
    bootstrap.ok && bootstrap.data && typeof bootstrap.data === 'object'
      ? String(
          (bootstrap.data as Record<string, unknown>).client &&
            typeof (bootstrap.data as Record<string, unknown>).client === 'object'
            ? ((bootstrap.data as Record<string, unknown>).client as Record<string, unknown>)
                .reference_currency ?? 'EUR'
            : 'EUR',
        )
          .trim()
          .toUpperCase()
      : 'EUR'

  const privyList = Array.isArray(
    (privyBalances.data as { balances?: unknown } | null)?.balances,
  )
    ? ((privyBalances.data as { balances: { asset?: string }[] }).balances ?? [])
    : []
  const symbols = [...new Set(privyList.map((b) => tickerToProviderSymbol(String(b.asset ?? ''))))]
    .filter(Boolean)
    .join(',')

  const marketRes =
    symbols.length > 0
      ? await fetchBackendJson(
          `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
        )
      : { ok: false, data: null }

  const crypto = resolveDashboardCryptoSummary(
    cryptoPositions.ok ? cryptoPositions.data : null,
    privyBalances.ok ? privyBalances.data : null,
    marketRes.ok ? marketRes.data : null,
    currency,
  )

  const partial =
    !bootstrap.ok ||
    !profile.ok ||
    !cash.ok ||
    !globalStatistics.ok ||
    !globalHistory.ok ||
    !cryptoPositions.ok ||
    !privyBalances.ok ||
    !placements.ok

  return NextResponse.json({
    bootstrap: bootstrap.ok ? bootstrap.data : null,
    profile: profile.ok ? profile.data : null,
    cash: cash.ok ? cash.data : null,
    globalStatistics: globalStatistics.ok ? globalStatistics.data : null,
    globalHistory: globalHistory.ok ? globalHistory.data : null,
    crypto,
    placements: placements.ok ? placements.data : null,
    notifications: notifications.ok ? notifications.data : null,
    newsWidget,
    privyPersonWallets: privyPersonWallets.ok ? privyPersonWallets.data : null,
    partial,
  })
}
