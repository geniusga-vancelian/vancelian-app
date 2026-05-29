import { NextResponse } from 'next/server'

import {
  assertExternalWalletMockDevRouteAvailable,
  externalWalletMockDevErrorResponse,
  linkLocalMockExternalWallet,
} from '@/lib/wallet/externalWalletMockDev'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

/** Lie le wallet externe mock local à la session portail courante. */
export async function POST() {
  try {
    assertExternalWalletMockDevRouteAvailable()

    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const wallet = await linkLocalMockExternalWallet(personId)
    return NextResponse.json({ ok: true, wallet })
  } catch (error) {
    const mapped = externalWalletMockDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
