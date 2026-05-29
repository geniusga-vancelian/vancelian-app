import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import {
  addMorphoSandboxYieldForPerson,
  assertMorphoSandboxDevRouteAvailable,
  morphoSandboxDevErrorResponse,
} from '@/lib/portal/morphoLocalSandboxDev'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

const bodySchema = z.object({
  amountUsdc: z.string().trim().min(1),
  vaultAddress: z.string().trim().optional(),
  walletAddress: z.string().trim().optional(),
})

/** Ajoute du rendement mock virtuel (sans toucher au cost basis). */
export async function POST(request: NextRequest) {
  try {
    assertMorphoSandboxDevRouteAvailable()

    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const parsed = bodySchema.parse(await request.json().catch(() => ({})))

    const result = await addMorphoSandboxYieldForPerson({
      personId,
      amountUsdc: parsed.amountUsdc,
      vaultAddress: parsed.vaultAddress,
      walletAddress: parsed.walletAddress,
    })

    return NextResponse.json({ ok: true, result })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ code: 'morpho.sandbox.invalid_request', issues: error.issues }, { status: 400 })
    }
    const mapped = morphoSandboxDevErrorResponse(error)
    return NextResponse.json(mapped.body, { status: mapped.status })
  }
}
