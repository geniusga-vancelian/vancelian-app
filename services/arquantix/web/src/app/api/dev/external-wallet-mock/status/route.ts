import { NextResponse } from 'next/server'

import {
  assertExternalWalletMockDevRouteAvailable,
  externalWalletMockDevErrorResponse,
  getLocalMockExternalWalletStatus,
} from '@/lib/wallet/externalWalletMockDev'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Statut du wallet externe mock local (dev sandbox uniquement). */
export async function GET() {
  try {
    assertExternalWalletMockDevRouteAvailable()

    const personId = await requirePortalPersonId()
    const status = await getLocalMockExternalWalletStatus({
      personId: personId instanceof NextResponse ? null : personId,
    })

    return NextResponse.json(status)
  } catch (error) {
    const mapped = externalWalletMockDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
