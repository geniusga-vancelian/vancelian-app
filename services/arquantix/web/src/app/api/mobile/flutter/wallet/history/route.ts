import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const period = request.nextUrl.searchParams.get('period') || 'ALL'
    const asset = request.nextUrl.searchParams.get('asset')
    const mode = request.nextUrl.searchParams.get('mode')
    const scope = request.nextUrl.searchParams.get('scope')
    const portfolioScope = request.nextUrl.searchParams.get('portfolio_scope')
    const portfolioId = request.nextUrl.searchParams.get('portfolio_id')
    const params = new URLSearchParams({ period })
    if (asset) params.set('asset', asset)
    if (mode) params.set('mode', mode)
    if (scope) params.set('scope', scope)
    if (portfolioScope) params.set('portfolio_scope', portfolioScope)
    if (portfolioId) params.set('portfolio_id', portfolioId)
    const url = buildBackendUrl(`/api/app/wallet/history?${params.toString()}`)
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
      headers: upstreamHeadersWithAuth(request),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/wallet/history GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
