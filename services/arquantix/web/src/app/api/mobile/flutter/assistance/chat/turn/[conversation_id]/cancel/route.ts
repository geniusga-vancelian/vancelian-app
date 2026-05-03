import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : POST /api/app/assistance/chat/turn/{conv_id}/cancel.
 *
 * MVP D.1.4.7 — annule volontairement le tour assistant en cours pour
 * cette conversation (équivalent du carré stop ChatGPT côté mobile).
 *
 * Effet côté serveur Python :
 *   1. Récupère la `Task` async associée à `conversation_id` dans le
 *      registre `_PENDING_STREAM_TASKS`.
 *   2. Appelle `task.cancel()` → `CancelledError` se propage à
 *      `stream_assistant_turn` qui n'attrape que `Exception` (pas
 *      `BaseException`) → **aucun message assistant n'est commité en
 *      BDD pour ce tour**.
 *
 * Sémantique :
 *   - Idempotent : 204 même s'il n'y a aucune génération en cours
 *     pour cette conv (déjà finie / jamais démarrée).
 *   - Ownership obligatoire côté Python : 404 si la conversation
 *     n'appartient pas au client courant (anti-IDOR).
 *   - Distinct du disconnect réseau : un client qui ferme juste sa
 *     connexion HTTP laisse la task vivante (commit du message). Seul
 *     cet endpoint explicite tue la task.
 */
const ROUTE = '[api/mobile/flutter/assistance/chat/turn/[id]/cancel POST]'

export async function POST(
  req: NextRequest,
  context: { params: Promise<{ conversation_id: string }> },
) {
  try {
    const { conversation_id } = await context.params
    const safeId = encodeURIComponent(conversation_id)
    const url = buildBackendUrl(
      `/api/app/assistance/chat/turn/${safeId}/cancel`,
    )
    const res = await fetch(url, {
      method: 'POST',
      headers: upstreamHeadersWithAuth(req),
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })

    if (res.status === 204) {
      return new NextResponse(null, { status: 204 })
    }

    const text = await res.text()
    let data: unknown = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = {
        error: {
          code: 'upstream_invalid_json',
          message: text.slice(0, 200),
        },
      }
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
      {
        status: 500,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      },
    )
  }
}
