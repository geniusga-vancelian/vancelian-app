import { NextRequest, NextResponse } from 'next/server'
import { getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'
import {
  loadPortalMarketsBundles,
  loadPortalMarketsDiscover,
  loadPortalMarketsTop,
} from '@/lib/portal/marketsUpstream'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

/**
 * Agrégateur markets (compat / preview navigation). Le client préfère désormais
 * les sections /markets/top + /markets/bundles + /markets/discover (progressif).
 */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

    const [top, bundlesSection, discover] = await Promise.all([
      loadPortalMarketsTop(),
      loadPortalMarketsBundles(bffOrigin),
      loadPortalMarketsDiscover(bffOrigin, locale),
    ])

    const payload: PortalMarketsPayload = {
      popular: top.popular,
      topGainers: top.topGainers,
      topLosers: top.topLosers,
      favorites: top.favorites,
      allCrypto: [],
      bundles: bundlesSection.bundles,
      news: discover.news,
      research: discover.research,
      marketDataPublicBaseUrl: top.marketDataPublicBaseUrl,
      currency: 'USD',
      partial: top.partial || bundlesSection.partial || discover.partial || bundlesSection.bundles.length === 0,
    }

    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/markets GET]', error)
    return NextResponse.json({
      popular: [],
      topGainers: [],
      topLosers: [],
      favorites: [],
      allCrypto: [],
      bundles: [],
      news: [],
      research: [],
      marketDataPublicBaseUrl: getMarketDataPublicBaseUrl(),
      currency: 'USD',
      partial: true,
    } satisfies PortalMarketsPayload)
  }
}
