import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { LombardMarketError } from '@/lib/portal/lombard/lombardMarket'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import { LombardBetaError, LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
import { logLombardQuoteBlocked, logLombardOpsEvent } from '@/lib/portal/lombard/lombardOpsLog'
import { runLombardPreBorrowSafetyChecks } from '@/lib/portal/lombard/lombardSafetyChecks'
import { lombardQuoteSchema } from '@/lib/portal/lombard/lombardValidation'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import {
  morphoRpcErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/portalWalletRouteHelpers'

function parseQuoteQuery(request: NextRequest) {
  const params = request.nextUrl.searchParams
  return lombardQuoteSchema.parse({
    collateral: params.get('collateral'),
    borrowAmount: params.get('borrow_amount') ?? params.get('borrowAmount'),
    walletAddress: params.get('wallet_address') ?? params.get('walletAddress'),
    targetLtvPercent: params.get('target_ltv_percent') ?? params.get('targetLtvPercent'),
  })
}

function logQuoteBlockedIfPossible(args: {
  personId: string | null
  parsed: z.infer<typeof lombardQuoteSchema> | null
  error: { code: string; message: string }
}) {
  if (!args.personId || !args.parsed) return
  logLombardQuoteBlocked({
    personId: args.personId,
    walletAddress: args.parsed.walletAddress,
    collateral: args.parsed.collateral,
    borrowAmount: args.parsed.borrowAmount,
    error: args.error,
  })
}

/** Quote inverse : montant USDC emprunté → garantie requise + niveau de sécurité. */
export async function GET(request: NextRequest) {
  let personId: string | null = null
  let parsed: z.infer<typeof lombardQuoteSchema> | null = null

  try {
    const auth = await requirePortalPersonId()
    if (auth instanceof NextResponse) return auth
    personId = auth

    if (!isLombardV1Enabled()) {
      return NextResponse.json({ code: 'lombard.disabled', message: 'Product unavailable.' }, { status: 503 })
    }

    parsed = parseQuoteQuery(request)
    await assertPortalWalletAddressOwnership({ personId, walletAddress: parsed.walletAddress })

    logLombardOpsEvent({
      code: 'lombard.quote_requested',
      level: 'info',
      message: 'Lombard quote requested.',
      personId,
      walletAddress: parsed.walletAddress,
      metadata: {
        collateral: parsed.collateral,
        borrowAmount: parsed.borrowAmount,
        targetLtvPercent: parsed.targetLtvPercent,
      },
    })

    const quote = await runLombardPreBorrowSafetyChecks({
      personId,
      collateral: parsed.collateral,
      borrowAmount: parsed.borrowAmount,
      walletAddress: parsed.walletAddress,
      targetLtvPercent: parsed.targetLtvPercent,
    })

    return NextResponse.json({ quote })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request data', issues: error.issues }, { status: 400 })
    }
    if (!parsed) {
      try {
        parsed = parseQuoteQuery(request)
      } catch {
        parsed = null
      }
    }
    if (error instanceof LombardQuoteError || error instanceof LombardMarketError) {
      logQuoteBlockedIfPossible({
        personId,
        parsed,
        error: { code: error.code, message: error.message },
      })
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    if (error instanceof LombardBetaError || error instanceof LombardSafetyError) {
      logQuoteBlockedIfPossible({
        personId,
        parsed,
        error: { code: error.code, message: error.message },
      })
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    const rpcResponse = morphoRpcErrorResponse(error, 'lombard.quote')
    if (rpcResponse) return rpcResponse
    console.error('[api/portal/lombard/quote GET]', error)
    const message = error instanceof Error ? error.message : 'Internal error.'
    return NextResponse.json({ code: 'lombard.quote_failed', message }, { status: 500 })
  }
}
