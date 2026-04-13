import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function GET(req: NextRequest) {
  try {
    const qs = req.nextUrl.searchParams.toString()
    const url = buildBackendUrl(`/api/app/orders${qs ? `?${qs}` : ''}`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(req), cache: 'no-store', signal: AbortSignal.timeout(5000) })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/orders GET]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const url = buildBackendUrl('/api/app/orders')
    const res = await fetch(url, {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(req),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/orders POST]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
