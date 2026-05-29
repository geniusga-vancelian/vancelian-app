import { NextResponse } from 'next/server'

import {
  assertMorphoSandboxDevRouteAvailable,
  morphoSandboxDevErrorResponse,
  seedMorphoSandboxForPerson,
} from '@/lib/portal/morphoLocalSandboxDev'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

/** Seed sandbox Morpho pour l’utilisateur portail connecté. */
export async function POST() {
  try {
    assertMorphoSandboxDevRouteAvailable()

    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const result = await seedMorphoSandboxForPerson({
      personId,
      withInitialPosition: true,
    })

    return NextResponse.json({ ok: true, result })
  } catch (error) {
    const mapped = morphoSandboxDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
