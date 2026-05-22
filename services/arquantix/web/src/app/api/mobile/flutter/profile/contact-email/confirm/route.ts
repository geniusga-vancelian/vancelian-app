import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import {
  mobileApiFailureResponse,
  mobileApiUpstreamInvalidResponse,
  readProxyJsonBody,
} from '@/lib/api/mobile-json-error'
import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

const ROUTE = '[api/mobile/flutter/profile/contact-email/confirm POST]'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const url = buildBackendUrl('/api/mobile/flutter/profile/contact-email/confirm')
    const res = await fetch(url, {
      method: 'POST',
      headers: upstreamHeadersWithAuth(request, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(15000),
    })

    const data = await readProxyJsonBody(res, ROUTE)
    return NextResponse.json(data, {
      status: res.status,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    })
  } catch (error) {
    const msg = error instanceof Error ? error.message : ''
    if (msg.includes('non-JSON') || msg.includes('empty body')) {
      return mobileApiUpstreamInvalidResponse(ROUTE)
    }
    return mobileApiFailureResponse(ROUTE, error)
  }
}
