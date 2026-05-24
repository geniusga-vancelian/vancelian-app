import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth } from '@/lib/api/mobile-upstream-auth'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const res = await fetch(buildBackendUrl('/api/swaps/quote'), {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(request),
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(20000),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/swaps/quote POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
