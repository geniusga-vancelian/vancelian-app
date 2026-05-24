import { NextRequest, NextResponse } from 'next/server'

import { mapPrivyEarnWalletAction } from '@/lib/portal/privyEarnFormat'
import { fetchPrivyWalletAction } from '@/lib/portal/privyServerClient'
import {
  privyEarnErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/privyEarnRouteHelpers'
import { assertPortalPrivyWalletOwnership } from '@/lib/portal/portalWalletOwnership'

type RouteContext = { params: Promise<{ actionId: string }> }

/** Statut d’une action wallet Privy (dépôt / retrait Earn). */
export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const { actionId } = await context.params
    const walletId = request.nextUrl.searchParams.get('privy_wallet_id')?.trim()
      || request.nextUrl.searchParams.get('privyWalletId')?.trim()

    if (!actionId?.trim() || !walletId) {
      return NextResponse.json(
        { code: 'privy.earn.invalid_request', message: 'actionId et privy_wallet_id requis.' },
        { status: 400 },
      )
    }

    await assertPortalPrivyWalletOwnership({ personId, privyWalletId: walletId })

    const row = await fetchPrivyWalletAction(walletId, actionId)
    return NextResponse.json({ action: mapPrivyEarnWalletAction(row) })
  } catch (error) {
    return privyEarnErrorResponse(error)
  }
}
