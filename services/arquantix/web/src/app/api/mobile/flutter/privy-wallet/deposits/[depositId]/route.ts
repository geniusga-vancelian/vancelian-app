import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

type RouteContext = { params: Promise<{ depositId: string }> }

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { depositId } = await context.params
    const url = buildBackendUrl(
      `/api/app/privy-wallet/deposits/${encodeURIComponent(depositId)}`,
    )
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
      headers: upstreamHeadersWithAuth(request),
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/privy-wallet/deposits/[depositId] GET]', error)
    return NextResponse.json(
      { error: 'Internal server error', message: 'The request could not be completed.' },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}
