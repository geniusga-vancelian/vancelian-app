import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const url = buildBackendUrl('/api/app/exchange/swap/preview')
    const res = await fetch(url, {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(request),
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(10000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/exchange/swap/preview POST]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
