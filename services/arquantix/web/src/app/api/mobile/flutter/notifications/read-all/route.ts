import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function POST(request: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/notifications/read-all')
    const res = await fetch(url, {
      method: 'POST',
      headers: upstreamHeadersWithAuth(request),
      signal: AbortSignal.timeout(5000),
    })
    if (res.status === 204) return new NextResponse(null, { status: 204 })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/notifications/read-all POST]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
