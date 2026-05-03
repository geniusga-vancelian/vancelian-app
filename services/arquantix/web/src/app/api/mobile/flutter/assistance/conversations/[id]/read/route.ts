import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : POST /api/app/assistance/conversations/{id}/read.
 *
 * MVP D.1.4.2 — marque la conversation comme « lue » (efface la pastille
 * côté liste). Appelée par Flutter après affichage d'une réponse assistant
 * (`/chat/turn` réussi) ou après chargement d'historique (`/messages`).
 *
 * Idempotent : 204 No Content systématique côté succès. 404 si la
 * conversation n'appartient pas au client courant.
 */
const ROUTE = '[api/mobile/flutter/assistance/conversations/[id]/read POST]'

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params
    const safeId = encodeURIComponent(id)
    const url = buildBackendUrl(
      `/api/app/assistance/conversations/${safeId}/read`,
    )
    const res = await fetch(url, {
      method: 'POST',
      headers: upstreamHeadersWithAuth(req),
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })

    // 204 = succès sans body — on relaie tel quel, sans tenter de parser.
    if (res.status === 204) {
      return new NextResponse(null, { status: 204 })
    }

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
