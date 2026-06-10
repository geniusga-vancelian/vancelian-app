import { NextRequest, NextResponse } from 'next/server'

import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET(
  _request: NextRequest,
  { params }: { params: { portfolioId: string } },
) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const portfolioId = (params.portfolioId ?? '').trim()
    const res = await portalUpstreamFetch(
      `/api/app/bundle/${encodeURIComponent(portfolioId)}/active-operation`,
      {
        method: 'GET',
        signal: AbortSignal.timeout(30_000),
      },
    )
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/active-operation GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
