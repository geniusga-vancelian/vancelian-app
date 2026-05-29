import { NextResponse } from 'next/server'

import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { externalWalletErrorResponse } from '@/lib/wallet/externalWalletRouteHelpers'
import { createExternalWalletNonce } from '@/lib/wallet/externalWalletVerification'

/** Génère un nonce anti-replay pour la signature de lien wallet externe. */
export async function POST() {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const payload = await createExternalWalletNonce(personId)
    return NextResponse.json(payload)
  } catch (error) {
    return externalWalletErrorResponse(error)
  }
}
