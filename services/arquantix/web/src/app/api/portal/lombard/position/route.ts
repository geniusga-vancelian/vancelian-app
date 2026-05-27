import { NextRequest, NextResponse } from 'next/server'

import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { LombardMarketError } from '@/lib/portal/lombard/lombardMarket'
import {
  buildLombardPositionsPayload,
  fetchLombardActivePositionsForWallet,
} from '@/lib/portal/lombard/lombardPositionService'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  morphoRpcErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/portalWalletRouteHelpers'

/** Positions Lombard actives (cbBTC/USDC, cbETH/USDC) pour le wallet connecté. */
export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const enabled = isLombardV1Enabled()
    if (!enabled) {
      return NextResponse.json(
        buildLombardPositionsPayload({
          enabled: false,
          walletAddress: '',
          positions: [],
        }),
      )
    }

    const walletAddress =
      request.nextUrl.searchParams.get('wallet_address')?.trim() ??
      request.nextUrl.searchParams.get('walletAddress')?.trim() ??
      ''

    if (!walletAddress || !isValidEvmAddress(walletAddress)) {
      return NextResponse.json({ error: 'Invalid wallet address.' }, { status: 400 })
    }

    await assertPortalWalletAddressOwnership({ personId, walletAddress })

    const positions = await fetchLombardActivePositionsForWallet(walletAddress)

    return NextResponse.json(
      buildLombardPositionsPayload({
        enabled: true,
        walletAddress,
        positions,
      }),
    )
  } catch (error) {
    if (error instanceof LombardMarketError) {
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    const rpcResponse = morphoRpcErrorResponse(error, 'lombard.position')
    if (rpcResponse) return rpcResponse
    console.error('[api/portal/lombard/position GET]', error)
    const message = error instanceof Error ? error.message : 'Internal error.'
    return NextResponse.json({ code: 'lombard.position_failed', message }, { status: 500 })
  }
}
