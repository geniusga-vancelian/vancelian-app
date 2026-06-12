import { NextRequest, NextResponse } from 'next/server'
import {
  parseMyBundles,
  parseSelfTradingCryptoPositionsPayload,
  parseWalletHistoryPoints,
  parseWalletHistoryPerformance,
} from '@/lib/portal/cryptoWalletFormat'
import {
  resolveTradingAvailableEurcFromDirectPayload,
  resolveTradingAvailableUsdcFromDirectPayload,
} from '@/lib/portal/vaultDepositValidation'
import {
  maybeApplyLombardWalletOverlay,
  resolveLombardOverlayWalletAddress,
  resolvePortalChainFromSearchParams,
} from '@/lib/portal/lombard/resolveLombardWalletOverlayForApi'
import { fetchPortalUpstreamJsonSafe, PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

async function fetchUpstreamJson(path: string, options?: { timeoutMs?: number }) {
  return fetchPortalUpstreamJsonSafe(path, options)
}

/** Hub wallet crypto — self-trading (direct_portfolio PE), bundles séparés via my-bundles. */
export async function GET(request: NextRequest) {
  try {
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
    fetchUpstreamJson('/api/app/crypto-positions/direct', {
      timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
    }),
    fetchUpstreamJson('/api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto'),
    fetchUpstreamJson('/api/app/bootstrap'),
    fetchUpstreamJson('/api/app/bundle/my-bundles'),
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

  const directPayload = directRes.ok && directRes.data ? directRes.data : null
  let positions = parseSelfTradingCryptoPositionsPayload(directPayload)
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
  const performance = history.ok ? parseWalletHistoryPerformance(history.data) : null
  const bundles = bundlesRes.ok ? parseMyBundles(bundlesRes.data) : []
  const tradingAvailableUsdc = directPayload
    ? resolveTradingAvailableUsdcFromDirectPayload(directPayload)
    : null
  const tradingAvailableEurc = directPayload
    ? resolveTradingAvailableEurcFromDirectPayload(directPayload)
    : null

  return NextResponse.json({
    currency,
    positions,
    bundles,
    historyPoints,
    performance,
    tradingAvailableUsdc,
    tradingAvailableEurc,
    source: 'direct',
    partial: !directRes.ok || !history.ok || !bundlesRes.ok,
  })
  } catch (error) {
    console.error('[api/portal/crypto-wallet GET]', error)
    return NextResponse.json({
      currency: 'EUR',
      positions: parseSelfTradingCryptoPositionsPayload(null),
      bundles: [],
      historyPoints: [],
      performance: null,
      tradingAvailableUsdc: null,
      tradingAvailableEurc: null,
      source: 'direct',
      partial: true,
    })
  }
}
