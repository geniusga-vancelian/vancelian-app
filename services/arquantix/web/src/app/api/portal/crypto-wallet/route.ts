import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import {
  buildPrivyWalletPositionsSummary,
  parseWalletHistoryPoints,
} from '@/lib/portal/cryptoWalletFormat'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

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

/** Hub wallet crypto — soldes réels Privy (aligné mobile + ledger on-chain). */
export async function GET(_request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const [privyRes, history, bootstrap] = await Promise.all([
    fetchUpstreamJson('/api/app/privy-wallet/balances'),
    fetchUpstreamJson(
      '/api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto',
    ),
    fetchUpstreamJson('/api/app/bootstrap'),
  ])

  if (!privyRes.ok || !privyRes.data) {
    return NextResponse.json({ error: 'privy_balances_unavailable' }, { status: 502 })
  }

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

  const balances = Array.isArray((privyRes.data as { balances?: unknown }).balances)
    ? ((privyRes.data as { balances: unknown[] }).balances as { asset?: string }[])
    : []
  const symbols = [...new Set(balances.map((b) => tickerToProviderSymbol(String(b.asset ?? ''))))]
    .filter(Boolean)
    .join(',')

  const marketRes =
    symbols.length > 0
      ? await fetchBackendJson(
          `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
        )
      : { ok: false, data: null }

  const positions = buildPrivyWalletPositionsSummary(
    privyRes.data,
    marketRes.ok ? marketRes.data : null,
    currency,
  )
  const historyPoints = history.ok ? parseWalletHistoryPoints(history.data) : []

  return NextResponse.json({
    currency,
    positions,
    bundles: [],
    historyPoints,
    source: 'privy',
    partial: !marketRes.ok || !history.ok,
  })
}
