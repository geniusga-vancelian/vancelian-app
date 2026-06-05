import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { buildLombardBorrowCapacity } from '@/lib/portal/lombard/lombardBorrowCapacity'
import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { LombardMarketError } from '@/lib/portal/lombard/lombardMarket'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import { lombardCapacityQuerySchema } from '@/lib/portal/lombard/lombardValidation'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import { morphoRpcErrorResponse } from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

/** Capacité max d'emprunt USDC (LTV 70 %) pour le curseur Borrow. */
export async function GET(request: NextRequest) {
  try {
    const auth = await requirePortalPersonId()
    if (auth instanceof NextResponse) return auth

    if (!isLombardV1Enabled()) {
      return NextResponse.json({ code: 'lombard.disabled', message: 'Product unavailable.' }, { status: 503 })
    }

    const params = request.nextUrl.searchParams
    const parsed = lombardCapacityQuerySchema.parse({
      collateral: params.get('collateral'),
      walletAddress: params.get('wallet_address') ?? params.get('walletAddress'),
      targetLtvPercent: params.get('target_ltv_percent') ?? params.get('targetLtvPercent'),
      portalWalletCollateralBalance:
        params.get('portal_wallet_collateral_balance') ??
        params.get('portalWalletCollateralBalance') ??
        undefined,
    })

    await assertPortalWalletAddressOwnership({ personId: auth, walletAddress: parsed.walletAddress })

    const capacity = await buildLombardBorrowCapacity({
      collateral: parsed.collateral,
      walletAddress: parsed.walletAddress,
      targetLtvPercent: parsed.targetLtvPercent,
      portalWalletCollateralBalance: parsed.portalWalletCollateralBalance,
    })

    return NextResponse.json({ capacity })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    if (error instanceof LombardQuoteError || error instanceof LombardMarketError) {
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    const rpcResponse = morphoRpcErrorResponse(error, 'lombard.capacity')
    if (rpcResponse) return rpcResponse
    console.error('[api/portal/lombard/capacity GET]', error)
    const message = error instanceof Error ? error.message : 'Internal error.'
    return NextResponse.json({ code: 'lombard.capacity_failed', message }, { status: 500 })
  }
}
