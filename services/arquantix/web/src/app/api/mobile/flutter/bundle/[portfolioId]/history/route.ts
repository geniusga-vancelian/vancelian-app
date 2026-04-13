import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(
  request: NextRequest,
  { params }: { params: { portfolioId: string } }
) {
  try {
    const { portfolioId } = params
    const period = request.nextUrl.searchParams.get('period') || 'ALL'
    const asset = request.nextUrl.searchParams.get('asset')
    const mode = request.nextUrl.searchParams.get('mode')
    const qs = new URLSearchParams({ period })
    if (asset) qs.set('asset', asset)
    if (mode) qs.set('mode', mode)
    const url = buildBackendUrl(`/api/app/bundle/${portfolioId}/history?${qs.toString()}`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/bundle/history GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
