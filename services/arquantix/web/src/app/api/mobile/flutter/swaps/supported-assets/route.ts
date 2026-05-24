import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(buildBackendUrl('/api/swaps/supported-assets'), {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/swaps/supported-assets GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
