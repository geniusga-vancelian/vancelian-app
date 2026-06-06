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
    const res = await portalUpstreamFetch(`/api/swaps/${swapId}/failure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15_000),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/swaps/[swapId]/failure POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
