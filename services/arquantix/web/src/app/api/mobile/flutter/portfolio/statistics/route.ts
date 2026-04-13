import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/portfolio/statistics')
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
      headers: upstreamHeadersWithAuth(request),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/portfolio/statistics GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
