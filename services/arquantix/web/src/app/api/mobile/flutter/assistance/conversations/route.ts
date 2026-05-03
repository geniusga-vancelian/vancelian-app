import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : GET /api/app/assistance/conversations.
 *
 * Liste paginée des conversations du client (D.1.4 — page « Mes
 * conversations »). Tous les filtres `status`, `limit`, `before` sont
 * transmis tels quels à l'upstream.
 */
const ROUTE = '[api/mobile/flutter/assistance/conversations GET]'

export async function GET(req: NextRequest) {
  try {
    const qs = req.nextUrl.searchParams.toString()
    const url = buildBackendUrl(
      `/api/app/assistance/conversations${qs ? `?${qs}` : ''}`,
    )
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(req),
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })
    const text = await res.text()
    let data: unknown = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = { error: { code: 'upstream_invalid_json', message: text.slice(0, 200) } }
    }
    return NextResponse.json(data, {
      status: res.status,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    })
  } catch (error) {
    console.error(ROUTE, error)
    return NextResponse.json(
      {
        error: {
          code: 'bff_error',
          message: 'The request could not be completed.',
        },
      },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}
