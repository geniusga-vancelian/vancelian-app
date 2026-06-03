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
    const batchId = request.nextUrl.searchParams.get('batch_id')?.trim()
    if (!portfolioId) {
      return NextResponse.json({ error: 'portfolio_id required' }, { status: 422 })
    }
    if (!batchId) {
      return NextResponse.json({ error: 'batch_id required' }, { status: 422 })
    }

    const qs = new URLSearchParams({
      portfolio_id: portfolioId,
      batch_id: batchId,
    })
    const res = await portalUpstreamFetch(
      `/api/app/bundle/reconciliation-state?${qs.toString()}`,
      { cache: 'no-store' },
    )
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/reconciliation-state GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
