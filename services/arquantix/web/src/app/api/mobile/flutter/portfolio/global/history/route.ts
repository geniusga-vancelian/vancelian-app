import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const period = searchParams.get('period') || 'ALL'
    const url = buildBackendUrl(`/api/app/portfolio/global/history?period=${period}`)
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
      headers: upstreamHeadersWithAuth(request),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/portfolio/global/history GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
