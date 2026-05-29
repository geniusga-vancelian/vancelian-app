import { NextRequest, NextResponse } from 'next/server'

import { canShowLombardDebugPanel } from '@/lib/portal/lombard/lombardDebugAccess'
import {
  isLombardV1BetaLimitsEnabled,
  isLombardWalletAllowlistConfigured,
} from '@/lib/portal/lombard/lombardBetaConfig'
import { isLombardV1Enabled, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { buildLombardBetaCapSnapshot } from '@/lib/portal/lombard/lombardQaContext'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'

/** QA debug context — only returned when debug panel is allowed (non-prod or admin-linked person). */
export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const debugVisible = await canShowLombardDebugPanel(personId)
    if (!debugVisible) {
      return NextResponse.json({ debugVisible: false })
    }

    const walletAddress =
      request.nextUrl.searchParams.get('wallet_address')?.trim() ??
      request.nextUrl.searchParams.get('walletAddress')?.trim() ??
      ''

    if (walletAddress && isValidEvmAddress(walletAddress)) {
      await assertPortalWalletAddressOwnership({ personId, walletAddress })
    }

    const betaCaps =
      walletAddress && isValidEvmAddress(walletAddress)
        ? await buildLombardBetaCapSnapshot(walletAddress)
        : null

    return NextResponse.json({
      debugVisible: true,
      featureEnabled: isLombardV1Enabled(),
      betaLimitsEnabled: isLombardV1BetaLimitsEnabled(),
      allowlistConfigured: isLombardWalletAllowlistConfigured(),
      maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
      betaCaps,
    })
  } catch (error) {
    console.error('[api/portal/lombard/qa-context GET]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
