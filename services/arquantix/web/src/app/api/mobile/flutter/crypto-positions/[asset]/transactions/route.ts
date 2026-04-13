import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ asset: string }> }
) {
  try {
    const { asset } = await params
    const url = buildBackendUrl(`/api/app/crypto-positions/${asset}/transactions`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/crypto-positions/[asset]/transactions GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
