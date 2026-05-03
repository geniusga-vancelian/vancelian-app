import { NextRequest, NextResponse } from 'next/server'

import { upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'
import { buildBackendUrl } from '@/lib/backend'

/**
 * BFF mobile → API Python : POST /api/app/assistance/voice/transcribe.
 *
 * MVP D.1.4.8 — Voice input (moteur Whisper uniquement).
 *
 * Le mobile (Flutter) appelle ce endpoint quand
 * `ASSISTANCE_VOICE_ENGINE=whisper`. Pour le moteur natif (défaut) la
 * transcription est locale et cet endpoint n'est PAS sollicité.
 *
 * Body : multipart/form-data avec un champ `audio` (m4a/wav/mp3/…).
 *        On forward le body brut tel quel (avec le boundary intact)
 *        pour ne pas avoir à re-parser/re-encoder le multipart, ce qui
 *        économise CPU + évite les bugs d'encodage binaire.
 *
 * Réponse : `{ "transcript": "…" }` (200) ou erreur structurée.
 *
 * Sécurité : le Bearer JWT est propagé via `upstreamHeadersWithAuth`.
 * Le backend Python applique :
 *   - 401 sans bearer
 *   - 403 si bearer valide mais sans client_id lié
 *   - 503 si `ASSISTANCE_VOICE_WHISPER_ENABLED=false` (kill-switch)
 *   - 413 si fichier > `ASSISTANCE_VOICE_MAX_BYTES` (10 MB par défaut)
 */
const ROUTE = '[api/mobile/flutter/assistance/voice/transcribe POST]'

export const runtime = 'nodejs'
// On ne préfère PAS edge ici : on manipule un body binaire potentiellement
// volumineux (10 MB), et certains runtimes edge limitent la taille.

export async function POST(req: NextRequest) {
  try {
    const url = buildBackendUrl('/api/app/assistance/voice/transcribe')

    // 1) Lecture du body brut. On préserve le content-type original
    //    qui contient le `boundary=…` essentiel au multipart.
    const body = await req.arrayBuffer()
    const contentType =
      req.headers.get('content-type') || 'multipart/form-data'

    // 2) Construction des headers : Bearer propagé + content-type original.
    //    On NE force PAS de Content-Length : fetch le calcule pour nous
    //    à partir du buffer (et certains proxys n'aiment pas un
    //    Content-Length manuel sur un binaire).
    const headers = upstreamHeadersWithAuth(req)
    headers.set('Content-Type', contentType)

    // 3) Timeout généreux : Whisper peut prendre ~3-10 s pour un audio
    //    de ~30 s. On laisse 60 s de marge.
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body,
      cache: 'no-store',
      signal: AbortSignal.timeout(60_000),
    })

    // 4) Réponse upstream : on s'attend à du JSON {transcript: "..."}.
    //    On forward tel quel pour préserver les codes d'erreur (503/413/...).
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
