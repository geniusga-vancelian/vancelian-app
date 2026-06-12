import { NextResponse } from 'next/server'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import { loadPortalMarketsTop } from '@/lib/portal/marketsUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalMarketsTopPayload } from '@/lib/portal/marketsTypes'

/** Section markets « top crypto » — chargée en premier, pilote le WS. */
export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    return NextResponse.json(await loadPortalMarketsTop())
  } catch (error) {
    console.error('[api/portal/markets/top GET]', error)
    return NextResponse.json({
      popular: [],
      topGainers: [],
      topLosers: [],
      favorites: [],
      marketDataPublicBaseUrl: getMarketDataPublicBaseUrl(),
      currency: 'USD',
      partial: true,
    } satisfies PortalMarketsTopPayload)
  }
}
