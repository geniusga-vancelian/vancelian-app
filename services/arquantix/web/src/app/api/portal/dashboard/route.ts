import { NextRequest, NextResponse } from 'next/server'
import {
  loadPortalDashboardCorePayload,
  loadPortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardUpstream'
import { mergePortalDashboardPayload } from '@/lib/portal/dashboardMerge'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { loadPortalTop10NewsWidget } from '@/lib/portal/loadTop10NewsWidget'

/** Agrégateur legacy — préférer core + portfolio + news-widget côté client. */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
  const origin = request.nextUrl.origin

  const [core, portfolio, newsWidget] = await Promise.all([
    loadPortalDashboardCorePayload(),
    loadPortalDashboardPortfolioPayload(),
    loadPortalTop10NewsWidget(locale, origin).catch(() => null),
  ])

  const payload = mergePortalDashboardPayload(core, portfolio, newsWidget)
  return NextResponse.json(payload)
}
