import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { buildLombardBorrowCapacity } from '@/lib/portal/lombard/lombardBorrowCapacity'
import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { LombardMarketError } from '@/lib/portal/lombard/lombardMarket'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import { lombardCollateralSchema, lombardTargetLtvPercentSchema } from '@/lib/portal/lombard/lombardValidation'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import {
  morphoRpcErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/portalWalletRouteHelpers'

const capacityQuerySchema = z.object({
  collateral: lombardCollateralSchema,
  walletAddress: z.string().trim().refine(isValidEvmAddress, 'Invalid wallet address.'),
  targetLtvPercent: lombardTargetLtvPercentSchema,
})

/** Capacité max d'emprunt USDC (LTV 70 %) pour le curseur Borrow. */
export async function GET(request: NextRequest) {
  try {
    const auth = await requirePortalPersonId()
    if (auth instanceof NextResponse) return auth

    if (!isLombardV1Enabled()) {
      return NextResponse.json({ code: 'lombard.disabled', message: 'Product unavailable.' }, { status: 503 })
    }

    const params = request.nextUrl.searchParams
    const parsed = capacityQuerySchema.parse({
      collateral: params.get('collateral'),
      walletAddress: params.get('wallet_address') ?? params.get('walletAddress'),
      targetLtvPercent: params.get('target_ltv_percent') ?? params.get('targetLtvPercent'),
    })

    await assertPortalWalletAddressOwnership({ personId: auth, walletAddress: parsed.walletAddress })

    const capacity = await buildLombardBorrowCapacity({
      collateral: parsed.collateral,
      walletAddress: parsed.walletAddress,
      targetLtvPercent: parsed.targetLtvPercent,
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
