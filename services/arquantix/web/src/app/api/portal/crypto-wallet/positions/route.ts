import { NextRequest, NextResponse } from 'next/server'
import {
  parseMyBundles,
  parseSelfTradingCryptoPositionsPayload,
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
import type { PortalCryptoWalletPositionsPayload } from '@/lib/portal/cryptoWalletTypes'

function emptyPositionsPayload(partial: boolean): PortalCryptoWalletPositionsPayload {
  return {
    currency: 'EUR',
    positions: parseSelfTradingCryptoPositionsPayload(null),
    bundles: [],
    source: 'direct',
    tradingAvailableUsdc: null,
    tradingAvailableEurc: null,
    partial,
  }
}

/** Hub wallet crypto — section positions + paniers (liste + totaux). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const portalChain = resolvePortalChainFromSearchParams(
      request.nextUrl.searchParams.get('portal_chain'),
    )
    const walletFromQuery =
      request.nextUrl.searchParams.get('wallet_address')?.trim() ??
      request.nextUrl.searchParams.get('walletAddress')?.trim() ??
      null
    const walletAddress = await resolveLombardOverlayWalletAddress({ request, walletFromQuery })

    const [directRes, bootstrap, bundlesRes] = await Promise.all([
      fetchPortalUpstreamJsonSafe('/api/app/crypto-positions/direct', {
        timeoutMs: PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS,
      }),
      fetchPortalUpstreamJsonSafe('/api/app/bootstrap'),
      fetchPortalUpstreamJsonSafe('/api/app/bundle/my-bundles'),
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
      console.warn('[api/portal/crypto-wallet/positions GET] Lombard overlay skipped:', error)
    }

    const bundles = bundlesRes.ok ? parseMyBundles(bundlesRes.data) : []

    const payload: PortalCryptoWalletPositionsPayload = {
      currency,
      positions,
      bundles,
      source: 'direct',
      tradingAvailableUsdc: directPayload
        ? resolveTradingAvailableUsdcFromDirectPayload(directPayload)
        : null,
      tradingAvailableEurc: directPayload
        ? resolveTradingAvailableEurcFromDirectPayload(directPayload)
        : null,
      partial: !directRes.ok || !bundlesRes.ok,
    }

    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/crypto-wallet/positions GET]', error)
    return NextResponse.json(emptyPositionsPayload(true))
  }
}
