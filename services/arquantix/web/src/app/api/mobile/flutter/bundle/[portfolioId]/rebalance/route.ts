import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function POST(
  _request: NextRequest,
  { params }: { params: { portfolioId: string } }
) {
  try {
    const { portfolioId } = params
    const url = buildBackendUrl(`/api/app/bundle/${portfolioId}/rebalance`)
    const res = await fetch(url, {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(_request),
      cache: 'no-store',
      signal: AbortSignal.timeout(60000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/bundle/rebalance POST]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
