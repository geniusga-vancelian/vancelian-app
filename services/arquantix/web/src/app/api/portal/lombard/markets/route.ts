import { NextRequest, NextResponse } from 'next/server'

import { isLombardV1Enabled, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  getLombardBetaLimitsForClient,
  isLombardV1BetaLimitsEnabled,
  isLombardWalletAllowlistConfigured,
} from '@/lib/portal/lombard/lombardBetaConfig'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { buildLombardMarketSummary, resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { getLombardMockMarketSummaries } from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Liste des marchés Lombard V1 (cbBTC/USDC, cbETH/USDC) avec données Morpho live. */
export async function GET(_request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    if (!isLombardV1Enabled()) {
      return NextResponse.json({
        enabled: false,
        markets: [],
        maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
        poweredBy: 'Morpho',
      })
    }

    const markets = isLombardMockEnabled()
      ? getLombardMockMarketSummaries()
      : await Promise.all(
          VANCELIAN_LOMBARD_V1.markets.map(async (row) => {
            const resolved = await resolveLombardMarket({ collateral: row.collateral })
            return buildLombardMarketSummary(resolved)
          }),
        )

    return NextResponse.json({
      enabled: true,
      markets,
      maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
      poweredBy: 'Morpho',
      mock: isLombardMockEnabled(),
      beta: {
        limitsEnabled: isLombardV1BetaLimitsEnabled(),
        allowlistConfigured: isLombardWalletAllowlistConfigured(),
        limits: isLombardV1BetaLimitsEnabled() ? getLombardBetaLimitsForClient() : null,
      },
    })
  } catch (error) {
    console.error('[api/portal/lombard/markets GET]', error)
    const message = error instanceof Error ? error.message : 'Internal error.'
    return NextResponse.json({ code: 'lombard.markets_failed', message }, { status: 500 })
  }
}
