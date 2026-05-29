import { NextResponse } from 'next/server'

import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { externalWalletErrorResponse } from '@/lib/wallet/externalWalletRouteHelpers'
import { listVerifiedExternalWallets } from '@/lib/wallet/externalWalletVerification'

/** Liste les wallets externes vérifiés liés à la session. */
export async function GET() {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const wallets = await listVerifiedExternalWallets(personId)
    return NextResponse.json({ wallets })
  } catch (error) {
    return externalWalletErrorResponse(error)
  }
}
