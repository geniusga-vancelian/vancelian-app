import { NextRequest, NextResponse } from 'next/server'

import { jsonHeadersWithUpstreamAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : POST /api/app/assistance/chat/turn.
 *
 * Pas de logique métier ici : on **propage** simplement le bearer client (Flutter)
 * vers FastAPI, qui résout `clientId`, vérifie le rate-limit (30/min/client par
 * défaut) et persiste la conversation. Tout le métier (OpenAI, DB) vit côté Python.
 */
const ROUTE = '[api/mobile/flutter/assistance/chat/turn POST]'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => null)
    if (!body || typeof body !== 'object') {
      return NextResponse.json(
        { error: { code: 'invalid_body', message: 'Body must be JSON object' } },
        { status: 400, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
      )
    }

    const url = buildBackendUrl('/api/app/assistance/chat/turn')
    const res = await fetch(url, {
      method: 'POST',
      headers: jsonHeadersWithUpstreamAuth(req),
      body: JSON.stringify(body),
      // L'appel OpenAI peut prendre quelques secondes : timeout généreux.
      signal: AbortSignal.timeout(30_000),
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
