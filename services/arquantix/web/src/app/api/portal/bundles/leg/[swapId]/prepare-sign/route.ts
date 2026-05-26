import { NextRequest, NextResponse } from 'next/server'

import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

type RouteContext = { params: Promise<{ swapId: string }> }

export async function POST(_request: NextRequest, context: RouteContext) {
  try {
    const token = await readPortalAccessToken()
    if (!token) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }

    const { swapId } = await context.params
    const res = await portalUpstreamFetch(`/api/app/bundle/leg/${encodeURIComponent(swapId)}/prepare-sign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
      signal: AbortSignal.timeout(30_000),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/portal/bundles/leg/prepare-sign POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
