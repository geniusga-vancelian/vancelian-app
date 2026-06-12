import { NextRequest, NextResponse } from 'next/server'
import { loadPortalMarketsBundles } from '@/lib/portal/marketsUpstream'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalMarketsBundlesPayload } from '@/lib/portal/marketsTypes'

/** Section markets « paniers crypto ». */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    return NextResponse.json(await loadPortalMarketsBundles(bffOrigin))
  } catch (error) {
    console.error('[api/portal/markets/bundles GET]', error)
    return NextResponse.json({ bundles: [], partial: true } satisfies PortalMarketsBundlesPayload)
  }
}
