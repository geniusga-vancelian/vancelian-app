import { NextResponse } from 'next/server'

import {
  assertExternalWalletMockDevRouteAvailable,
  externalWalletMockDevErrorResponse,
  unlinkLocalMockExternalWallet,
} from '@/lib/wallet/externalWalletMockDev'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

/** Dissocie le wallet externe mock local de la session portail courante. */
export async function DELETE() {
  try {
    assertExternalWalletMockDevRouteAvailable()

    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await unlinkLocalMockExternalWallet(personId)
    return NextResponse.json({ ok: true })
  } catch (error) {
    const mapped = externalWalletMockDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
