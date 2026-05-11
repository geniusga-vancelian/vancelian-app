/**
 * Helper proxy pour les routes admin d'observabilité Assistance (PR 4B/4C).
 *
 * Source de vérité = API Python (FastAPI
 * `services/assistance/admin_observability_router.py`).
 */
import { NextResponse } from 'next/server'
import { getSessionFromCookie, type AdminWebSession } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export const dynamic = 'force-dynamic'

const TIMEOUT_MS = 15_000

type ProxyResult =
  | { ok: true; session: AdminWebSession; headers: Record<string, string> }
  | { ok: false; response: NextResponse }

async function authorizeAndPrepareHeaders(): Promise<ProxyResult> {
  const session = await getSessionFromCookie()
  if (!session) {
    return {
      ok: false,
      response: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }),
    }
  }
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Actor-Type': 'admin',
    'X-Actor-Roles': 'admin',
    'X-Actor-Id': session.userEmail || `user:${session.userId}`,
  }
  return { ok: true, session, headers }
}

/**
 * Forward un GET vers `/api/admin/assistance/observability<subpath>` côté FastAPI.
 *
 * @param subpath ex. `"/summary"`, `"/data-need-gaps"`, `"/tool-usage"`.
 */
export async function forwardObservabilityRequest(
  subpath: string,
  query?: Record<string, string | undefined | null>,
): Promise<NextResponse> {
  const auth = await authorizeAndPrepareHeaders()
  if (!auth.ok) return auth.response

  const url = new URL(
    buildBackendUrl(`/api/admin/assistance/observability${subpath}`),
  )
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '')
        url.searchParams.set(k, String(v))
    }
  }

  try {
    const upstream = await fetch(url.toString(), {
      method: 'GET',
      headers: auth.headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })

    const text = await upstream.text()
    let json: unknown = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      return new NextResponse(text, {
        status: upstream.status,
        headers: {
          'Content-Type': upstream.headers.get('content-type') || 'text/plain',
        },
      })
    }
    return NextResponse.json(json, { status: upstream.status })
  } catch (error) {
    console.error('[assistance-observability-proxy]', subpath, error)
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 502 },
    )
  }
}
