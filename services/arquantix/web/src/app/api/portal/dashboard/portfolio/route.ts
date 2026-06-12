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
  const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim() || undefined
  try {
    const payload = await loadPortalDashboardPortfolioPayload(personId, {
      currencyHint,
      walletAddress,
    })
    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/dashboard/portfolio GET]', error)
    return NextResponse.json({
      crypto: null,
      placements: null,
      savings: { positions_count: 0, positions: [], total_value_eur: 0, total_value_usd: 0 },
      partial: true,
    })
  }
}
