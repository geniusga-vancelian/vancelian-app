import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl, getBackendUrlResolution } from '@/lib/backend'

/**
 * Proxy PDF : Flutter → BFF → API Python `GET /api/app/transactions/{id}/operation-statement.pdf`.
 */
const LOG_PREFIX = '[operation-statement.pdf][BFF]'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const url = buildBackendUrl(`/api/app/transactions/${id}/operation-statement.pdf`)
    const resolution = getBackendUrlResolution()
    console.info('OPERATION_STATEMENT_PDF_BFF_ENTRY', {
      transactionId: id,
      backendUrl: url,
      backendEnvSource: resolution.source,
      backendBaseUrl: resolution.baseUrl,
    })
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

    const upstreamType = res.headers.get('content-type')
    console.info('OPERATION_STATEMENT_PDF_UPSTREAM_STATUS', {
      transactionId: id,
      status: res.status,
      ok: res.ok,
      contentType: upstreamType ?? '(missing)',
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
    const upstreamTypeFinal = res.headers.get('content-type')
    // Erreurs FastAPI = JSON : ne pas forcer application/pdf (sinon le client ne parse pas le message).
    const contentType =
      upstreamTypeFinal && upstreamTypeFinal.trim().length > 0
        ? upstreamTypeFinal
        : res.ok
          ? 'application/pdf'
          : 'application/json; charset=utf-8'

    return new NextResponse(buf, {
      status: res.status,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'no-store',
      },
    })
  } catch (error) {
    console.error('OPERATION_STATEMENT_PDF_BFF_FETCH_FAILED', error)
    console.error(`${LOG_PREFIX} fetch failed`, error)
    return NextResponse.json(
      {
        detail: 'The request could not be completed.',
        error: 'Internal server error',
        message: 'The request could not be completed.',
      },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } }
    )
  }
}
