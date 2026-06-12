import { NextRequest, NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { loadPortalInvestOffers } from '@/lib/portal/investUpstream'
import type { PortalInvestOffersPayload } from '@/lib/portal/investTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'

/** Section invest « offres exclusives » — chargée indépendamment (shimmer dédié). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const origin = resolvePortalBffOrigin(request.nextUrl.origin)
  const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

  try {
    return NextResponse.json(await loadPortalInvestOffers(origin, locale))
  } catch (error) {
    console.error('[api/portal/invest/offers GET]', error)
    return NextResponse.json({ offers: [], partial: true } satisfies PortalInvestOffersPayload)
  }
}
