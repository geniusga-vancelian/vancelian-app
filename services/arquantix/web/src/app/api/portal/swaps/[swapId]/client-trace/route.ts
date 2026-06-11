import { NextRequest, NextResponse } from 'next/server'

import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

type RouteContext = { params: Promise<{ swapId: string }> }

export async function POST(request: NextRequest, context: RouteContext) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const { swapId } = await context.params
    const body = await request.json()
    const res = await portalUpstreamFetch(`/api/swaps/${swapId}/client-trace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10_000),
    })
    if (res.status === 204) {
      return new NextResponse(null, { status: 204 })
    }
    const data = await res.json().catch(() => ({}))
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/swaps/[swapId]/client-trace POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
