import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl, getBackendUrlResolution } from '@/lib/backend'

/**
 * Proxy PDF : Flutter appelle le BFF Next avec le même Bearer que les autres routes `/api/mobile/flutter/*`,
 * le BFF transmet vers l’API Python `GET /api/app/euro-account/statement.pdf`.
 */
const LOG_PREFIX = '[statement.pdf][BFF]'

export async function GET(request: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/euro-account/statement.pdf')
    const resolution = getBackendUrlResolution()
    console.info(`${LOG_PREFIX} upstream request`, {
      method: 'GET',
      url,
      backendEnvSource: resolution.source,
      backendBaseUrl: resolution.baseUrl,
    })

    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(120_000),
      headers: upstreamHeadersWithAuth(request),
    })

    if (!res.ok) {
      let bodyExcerpt = ''
      try {
        const text = await res.clone().text()
        bodyExcerpt = text.slice(0, 500)
      } catch {
        bodyExcerpt = '(could not read body as text)'
      }
      const contentType = res.headers.get('content-type')
      console.error(`${LOG_PREFIX} upstream response not OK`, {
        status: res.status,
        contentType: contentType ?? '(missing)',
        bodyExcerpt,
      })
    }

    const buf = await res.arrayBuffer()
    const upstreamType = res.headers.get('content-type')
    const contentType =
      upstreamType && upstreamType.trim().length > 0 ? upstreamType : 'application/pdf'

    return new NextResponse(buf, {
      status: res.status,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'no-store',
      },
    })
  } catch (error) {
    console.error(`${LOG_PREFIX} fetch failed (network/timeout/connection)`, error)
    return NextResponse.json(
      { error: 'Internal server error', message: 'The request could not be completed.' },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}
