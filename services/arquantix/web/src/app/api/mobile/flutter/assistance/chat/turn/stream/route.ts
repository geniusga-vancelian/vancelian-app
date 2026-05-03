import { NextRequest, NextResponse } from 'next/server'

import { jsonHeadersWithUpstreamAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : POST /api/app/assistance/chat/turn/stream.
 *
 * MVP D.1.4.5 (phase 2) — relais Server-Sent Events.
 *
 * Spécificités :
 *  - Pass-through pur du body upstream (pas de `await text()` qui
 *    bufferiserait toute la réponse). On forward `upstream.body` à la
 *    `Response` Next.js, qui supporte les Web Streams nativement.
 *  - Désactive `cache` et fixe les headers SSE explicitement (le
 *    Content-Type `text/event-stream` est crucial côté client).
 *  - `dynamic = 'force-dynamic'` : force le runtime non-statique pour
 *    cette route (sinon Next.js peut tenter du caching).
 *  - PAS de `AbortSignal.timeout(...)` : un stream peut durer 30+ s
 *    légitimement, on ne l'interrompt pas côté BFF.
 *  - Le serveur Python continue le pipeline OpenAI même si le client
 *    se déconnecte — voir `_PENDING_STREAM_TASKS` côté API. Le commit
 *    BDD a toujours lieu.
 *
 * Authentification : `upstreamHeadersWithAuth` propage le bearer JWT du
 * client mobile vers Python.
 */
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const ROUTE = '[api/mobile/flutter/assistance/chat/turn/stream POST]'

export async function POST(req: NextRequest) {
  try {
    // On parse / re-sérialise comme le proxy `/chat/turn` non-stream pour
    // garantir un body JSON valide ET un `Content-Type: application/json`
    // sur la requête upstream (sinon FastAPI répond 422 "Input should be a
    // valid dictionary or object").
    const body = await req.json().catch(() => null)
    if (!body || typeof body !== 'object') {
      return NextResponse.json(
        { error: { code: 'invalid_body', message: 'Body must be JSON object' } },
        { status: 400, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
      )
    }

    const url = buildBackendUrl('/api/app/assistance/chat/turn/stream')
    const upstream = await fetch(url, {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(req),
      body: JSON.stringify(body),
      cache: 'no-store',
      // pas de timeout — un stream peut durer.
    })

    // Erreur upstream (401, 429, 4xx, 5xx) — on relaie le body JSON.
    if (!upstream.ok) {
      const text = await upstream.text()
      let data: unknown = null
      try {
        data = text ? JSON.parse(text) : null
      } catch {
        data = { error: { code: 'upstream_invalid_json', message: text.slice(0, 200) } }
      }
      return NextResponse.json(data, {
        status: upstream.status,
        headers: { 'Content-Type': 'application/json; charset=utf-8' },
      })
    }

    // Succès : on pass-through le stream au client.
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
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
