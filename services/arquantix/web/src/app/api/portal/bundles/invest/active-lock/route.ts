import { NextRequest, NextResponse } from 'next/server'

import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET(request: NextRequest) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const portfolioId = request.nextUrl.searchParams.get('portfolio_id')?.trim()
    if (!portfolioId) {
      return NextResponse.json({ error: 'portfolio_id required' }, { status: 422 })
    }

    const res = await portalUpstreamFetch(
      `/api/app/bundle/invest/active-lock?portfolio_id=${encodeURIComponent(portfolioId)}`,
      { cache: 'no-store' },
    )
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/invest/active-lock GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
