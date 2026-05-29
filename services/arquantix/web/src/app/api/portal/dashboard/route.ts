import { NextRequest, NextResponse } from 'next/server'
import {
  loadPortalDashboardCorePayload,
  loadPortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardUpstream'
import { mergePortalDashboardPayload } from '@/lib/portal/dashboardMerge'
import { readPortalPersonIdFromToken, PortalAuthError } from '@/lib/portal/portalJwt'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { loadPortalTop10NewsWidget } from '@/lib/portal/loadTop10NewsWidget'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

/** Agrégateur legacy — préférer core + portfolio + news-widget côté client. */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  let personId: string
  try {
    personId = readPortalPersonIdFromToken(token)
  } catch (error) {
    if (error instanceof PortalAuthError) {
      return NextResponse.json({ error: 'unauthorized', message: error.message }, { status: 401 })
    }
    throw error
  }

  const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
  const origin = request.nextUrl.origin

  const [core, portfolio, newsWidget] = await Promise.all([
    loadPortalDashboardCorePayload(),
    loadPortalDashboardPortfolioPayload(personId),
    loadPortalTop10NewsWidget(locale, origin).catch(() => null),
  ])

  const payload = mergePortalDashboardPayload(core, portfolio, newsWidget)
  return NextResponse.json(payload)
}
