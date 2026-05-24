import { NextRequest, NextResponse } from 'next/server'
import { loadPortalDashboardPortfolioPayload } from '@/lib/portal/dashboardUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/** Dashboard portail — crypto + placements (après le core). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const currencyHint = request.nextUrl.searchParams.get('currency')?.trim() || undefined
  const payload = await loadPortalDashboardPortfolioPayload(currencyHint)
  return NextResponse.json(payload)
}
