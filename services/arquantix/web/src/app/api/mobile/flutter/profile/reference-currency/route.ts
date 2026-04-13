import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json()
    const url = buildBackendUrl('/api/app/profile/reference-currency')
    const res = await fetch(url, {
      method: 'PATCH',
      headers: jsonHeadersWithUpstreamAuth(request),
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/profile/reference-currency PATCH]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
