import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(req: NextRequest) {
  try {
    const qs = req.nextUrl.searchParams.toString()
    const url = buildBackendUrl(`/api/app/notifications${qs ? `?${qs}` : ''}`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(req), cache: 'no-store', signal: AbortSignal.timeout(5000) })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/notifications GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
