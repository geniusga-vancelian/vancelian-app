import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(
  request: NextRequest,
  { params }: { params: { asset: string } }
) {
  try {
    const { asset } = params
    const qs = new URLSearchParams()
    const portfolioScope = request.nextUrl.searchParams.get('portfolio_scope')
    const portfolioId = request.nextUrl.searchParams.get('portfolio_id')
    if (portfolioScope) qs.set('portfolio_scope', portfolioScope)
    if (portfolioId) qs.set('portfolio_id', portfolioId)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    const url = buildBackendUrl(`/api/app/wallet/statistics/${encodeURIComponent(asset)}${suffix}`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(request),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/wallet/statistics GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
