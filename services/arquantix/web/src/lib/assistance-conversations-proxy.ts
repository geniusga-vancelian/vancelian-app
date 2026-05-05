/**
 * Helpers partagés pour les routes proxy
 * `/api/admin/assistance/conversations/...` (admin monitoring v1, read-only).
 *
 * Source de vérité = API Python (FastAPI router
 * `services/assistance/admin_conversations_router.py`). Le BFF Next.js sert
 * uniquement de proxy authentifié : on valide la session admin web
 * (`getSessionFromCookie`), puis on relaie vers FastAPI avec les en-têtes
 * `X-Actor-*` qui activent le guard `require_admin_or_ops()`.
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
 * Forward un GET vers `/api/admin/assistance/conversations<path>` côté FastAPI.
 *
 * @param subpath ex. `""` (list), `"/<conversationId>"`, `"/<conversationId>/decisions"`.
 * @param query   paramètres URL à concaténer.
 */
export async function forwardConversationsRequest(
  subpath: string,
  query?: Record<string, string | undefined | null>,
): Promise<NextResponse> {
  const auth = await authorizeAndPrepareHeaders()
  if (!auth.ok) return auth.response

  const url = new URL(
    buildBackendUrl(`/api/admin/assistance/conversations${subpath}`),
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
    console.error('[assistance-conversations-proxy]', subpath, error)
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 502 },
    )
  }
}
