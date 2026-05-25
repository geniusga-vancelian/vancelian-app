import { NextResponse } from 'next/server'

import {
  assertMorphoSandboxDevRouteAvailable,
  getMorphoSandboxDevStatus,
  morphoSandboxDevErrorResponse,
} from '@/lib/portal/morphoLocalSandboxDev'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Statut du sandbox Morpho local (dev uniquement). */
export async function GET() {
  try {
    assertMorphoSandboxDevRouteAvailable()

    const personId = await requirePortalPersonId()
    const status = await getMorphoSandboxDevStatus({
      personId: personId instanceof NextResponse ? null : personId,
    })

    return NextResponse.json(status)
  } catch (error) {
    const mapped = morphoSandboxDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
