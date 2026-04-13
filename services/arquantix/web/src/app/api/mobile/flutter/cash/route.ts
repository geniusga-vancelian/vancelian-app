import { NextRequest, NextResponse } from 'next/server'

import {
  mobileApiFailureResponse,
  mobileApiUpstreamInvalidResponse,
  readProxyJsonBody,
} from '@/lib/api/mobile-json-error'
import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

const ROUTE = '[api/mobile/flutter/cash GET]'

export async function GET(request: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/cash')
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
      headers: upstreamHeadersWithAuth(request),
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
