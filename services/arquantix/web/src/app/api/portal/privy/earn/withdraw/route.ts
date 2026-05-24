import { NextRequest, NextResponse } from 'next/server'

import { executePrivyEarnOperation, PrivyEarnVaultConfigError } from '@/lib/portal/morphoPrivyEarnService'
import {
  parseAuthHeaders,
  parseEarnAmount,
  parsePrivyWalletId,
  parseRequiredIdempotencyKey,
  parseVaultId,
  privyEarnErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/privyEarnRouteHelpers'
import { assertPortalPrivyWalletOwnership } from '@/lib/portal/portalWalletOwnership'

/** Retrait depuis un vault Privy Earn (Morpho). */
export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const body = await request.json().catch(() => null)
    const vaultId = parseVaultId(body)
    const walletId = parsePrivyWalletId(body)
    const amount = parseEarnAmount(body)
    const idempotencyKey = parseRequiredIdempotencyKey(body)
    if (!vaultId || !walletId || !amount || !idempotencyKey) {
      return NextResponse.json(
        {
          code: 'privy.earn.invalid_request',
          message: 'vault_id, privy_wallet_id, amount (> 0) et idempotency_key requis.',
        },
        { status: 400 },
      )
    }

    await assertPortalPrivyWalletOwnership({ personId, privyWalletId: walletId })

    const auth = parseAuthHeaders(body)
    const action = await executePrivyEarnOperation({
      personId,
      walletId,
      vaultId,
      operation: 'withdraw',
      amount,
      idempotencyKey,
      authorizationSignature: auth.authorizationSignature,
      requestExpiry: auth.requestExpiry,
    })
    return NextResponse.json({ action })
  } catch (error) {
    if (error instanceof PrivyEarnVaultConfigError) {
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    return privyEarnErrorResponse(error)
  }
}
