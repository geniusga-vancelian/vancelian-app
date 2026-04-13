import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(
  _request: NextRequest,
  { params }: { params: { portfolioId: string } }
) {
  try {
    const { portfolioId } = params
    const url = buildBackendUrl(`/api/app/bundle/${portfolioId}/statistics`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(_request),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/bundle/statistics GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
