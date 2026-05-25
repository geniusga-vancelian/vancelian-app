import { NextResponse } from 'next/server'

import {
  assertMorphoSandboxDevRouteAvailable,
  morphoSandboxDevErrorResponse,
  resetMorphoSandboxForPerson,
} from '@/lib/portal/morphoLocalSandboxDev'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Supprime les données sandbox Morpho de l’utilisateur connecté. */
export async function POST() {
  try {
    assertMorphoSandboxDevRouteAvailable()

    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const result = await resetMorphoSandboxForPerson(personId)

    return NextResponse.json({ ok: true, result })
  } catch (error) {
    const mapped = morphoSandboxDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
