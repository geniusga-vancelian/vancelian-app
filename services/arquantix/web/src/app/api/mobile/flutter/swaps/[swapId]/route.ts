import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

type RouteContext = { params: Promise<{ swapId: string }> }

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { swapId } = await context.params
    const res = await fetch(buildBackendUrl(`/api/swaps/${swapId}`), {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/swaps/[swapId] GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest, context: RouteContext) {
  try {
    const { swapId } = await context.params
    const body = await request.json()
    const res = await fetch(buildBackendUrl(`/api/swaps/${swapId}/submit`), {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(request),
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/swaps/[swapId] POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
