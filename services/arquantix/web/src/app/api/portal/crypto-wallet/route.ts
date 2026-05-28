import { NextRequest, NextResponse } from 'next/server'
import {
  parseMyBundles,
  parseSelfTradingCryptoPositionsPayload,
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

/** Hub wallet crypto — self-trading (direct_portfolio PE), bundles séparés via my-bundles. */
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

  const [directRes, history, bootstrap, bundlesRes] = await Promise.all([
    fetchUpstreamJson('/api/app/crypto-positions/direct'),
    fetchUpstreamJson(
      '/api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto',
    ),
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson('/api/app/bundle/my-bundles'),
  ])

  if (!directRes.ok || !directRes.data) {
    return NextResponse.json({ error: 'direct_positions_unavailable' }, { status: 502 })
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

  let positions = parseSelfTradingCryptoPositionsPayload(directRes.data)
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
    source: 'direct',
    partial: !history.ok || !bundlesRes.ok,
  })
}
