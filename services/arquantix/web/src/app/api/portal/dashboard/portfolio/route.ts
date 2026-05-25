import { NextRequest, NextResponse } from 'next/server'
import { loadPortalDashboardPortfolioPayload } from '@/lib/portal/dashboardUpstream'
import { readPortalPersonIdFromToken, PortalAuthError } from '@/lib/portal/portalJwt'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/** Dashboard portail — crypto + placements + épargne (après le core). */
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

  const currencyHint = request.nextUrl.searchParams.get('currency')?.trim() || undefined
  const payload = await loadPortalDashboardPortfolioPayload(personId, currencyHint)
  return NextResponse.json(payload)
}
