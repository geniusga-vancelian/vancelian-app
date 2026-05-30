import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

type RouteContext = { params: Promise<{ swapId: string }> }

export async function POST(request: NextRequest, context: RouteContext) {
  try {
    const { swapId } = await context.params
    const body = await request.json()
    const res = await fetch(buildBackendUrl(`/api/swaps/${swapId}/approval`), {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(request),
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/swaps/[swapId]/approval POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
