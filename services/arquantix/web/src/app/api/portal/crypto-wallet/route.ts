import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { assetToMarketProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import {
  buildPrivyWalletPositionsSummary,
  parseMyBundles,
  parseWalletHistoryPoints,
} from '@/lib/portal/cryptoWalletFormat'
import {
  maybeApplyLombardWalletOverlay,
  resolveLombardOverlayWalletAddress,
  resolvePortalChainFromSearchParams,
} from '@/lib/portal/lombard/resolveLombardWalletOverlayForApi'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

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

/** Hub wallet crypto — soldes Privy enrichis Lombard (locked / USDC empruntés). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const personId = await requirePortalPersonId()
  if (personId instanceof NextResponse) return personId

  const portalChain = resolvePortalChainFromSearchParams(
    request.nextUrl.searchParams.get('portal_chain'),
  )
  const walletFromQuery =
    request.nextUrl.searchParams.get('wallet_address')?.trim() ??
    request.nextUrl.searchParams.get('walletAddress')?.trim() ??
    null
  const walletAddress = await resolveLombardOverlayWalletAddress({
    request,
    walletFromQuery,
  })

  const [privyRes, history, bootstrap, bundlesRes] = await Promise.all([
    fetchUpstreamJson('/api/app/privy-wallet/balances'),
    fetchUpstreamJson(
      '/api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto',
    ),
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson('/api/app/bundle/my-bundles'),
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
  const symbols = [...new Set(balances.map((b) => assetToMarketProviderSymbol(String(b.asset ?? ''))))]
    .filter(Boolean)
    .join(',')

  const marketRes =
    symbols.length > 0
      ? await fetchBackendJson(
          `/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
        )
      : { ok: false, data: null }

  let positions = buildPrivyWalletPositionsSummary(
    privyRes.data,
    marketRes.ok ? marketRes.data : null,
    currency,
  )
  try {
    positions = await maybeApplyLombardWalletOverlay({
      personId,
      portalChain,
      walletAddress,
      summary: positions,
    })
  } catch (error) {
    console.warn('[api/portal/crypto-wallet GET] Lombard overlay skipped:', error)
  }
  const historyPoints = history.ok ? parseWalletHistoryPoints(history.data) : []
  const bundles = bundlesRes.ok ? parseMyBundles(bundlesRes.data) : []

  return NextResponse.json({
    currency,
    positions,
    bundles,
    historyPoints,
    source: 'privy',
    partial: !marketRes.ok || !history.ok || !bundlesRes.ok,
  })
}
