import { NextRequest, NextResponse } from 'next/server'

import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'
import { externalWalletErrorResponse } from '@/lib/wallet/externalWalletRouteHelpers'
import { revokeExternalWallet } from '@/lib/wallet/externalWalletVerification'

type RouteContext = { params: Promise<{ id: string }> }

/** Révoque le lien d’un wallet externe vérifié. */
export async function DELETE(_request: NextRequest, context: RouteContext) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const { id } = await context.params
    if (!id?.trim()) {
      return NextResponse.json({ code: 'wallet.invalid_request', message: 'Identifiant manquant.' }, { status: 400 })
    }

    await revokeExternalWallet({ personId, walletId: id.trim() })
    return NextResponse.json({ ok: true })
  } catch (error) {
    return externalWalletErrorResponse(error)
  }
}
