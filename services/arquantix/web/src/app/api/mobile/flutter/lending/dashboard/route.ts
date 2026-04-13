import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(request: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/lending/dashboard')
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
      signal: AbortSignal.timeout(10000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/lending/dashboard GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
