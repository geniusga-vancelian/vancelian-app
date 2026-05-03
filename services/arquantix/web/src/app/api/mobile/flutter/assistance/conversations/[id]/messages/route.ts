import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : GET /api/app/assistance/conversations/{id}/messages.
 *
 * Reprise visuelle d'une conversation (MVP D.1.6) : Flutter appelle cette route
 * au mount du Search Screen quand un `conversation_id` a été restauré depuis
 * `flutter_secure_storage`. Tout le contrôle d'appartenance client est fait
 * côté Python (404 si la conversation n'est pas à l'utilisateur).
 */
const ROUTE = '[api/mobile/flutter/assistance/conversations/[id]/messages GET]'

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params
    const safeId = encodeURIComponent(id)
    const qs = req.nextUrl.searchParams.toString()
    const url = buildBackendUrl(
      `/api/app/assistance/conversations/${safeId}/messages${qs ? `?${qs}` : ''}`,
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
