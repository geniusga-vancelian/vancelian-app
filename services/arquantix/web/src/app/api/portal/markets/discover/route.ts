import { NextRequest, NextResponse } from 'next/server'
import { loadPortalMarketsDiscover } from '@/lib/portal/marketsUpstream'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import type { PortalMarketsDiscoverPayload } from '@/lib/portal/marketsTypes'

/** Section markets éditoriale (actualités + analyses). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    return NextResponse.json(await loadPortalMarketsDiscover(bffOrigin, locale))
  } catch (error) {
    console.error('[api/portal/markets/discover GET]', error)
    return NextResponse.json({
      news: [],
      research: [],
      partial: true,
    } satisfies PortalMarketsDiscoverPayload)
  }
}
