/**
 * Helpers partagés pour les routes proxy `/api/admin/assistance/knowledge/...`.
 *
 * Source de vérité de la table `product_knowledge` = API Python (SQLAlchemy).
 * Le BFF Next.js sert uniquement de proxy authentifié : on valide la session
 * admin web (`getSessionFromCookie`), puis on relaie vers FastAPI avec les
 * en-têtes `X-Actor-*` qui activent le guard `require_admin_or_ops()`.
 */
import { NextResponse } from 'next/server'
import { getSessionFromCookie, type AdminWebSession } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export const dynamic = 'force-dynamic'

const TIMEOUT_MS = 15_000

export type ProxyResult =
  | { ok: true; session: AdminWebSession; headers: Record<string, string> }
  | { ok: false; response: NextResponse }

/**
 * Vérifie la session admin web et prépare les en-têtes upstream pour FastAPI.
 *
 * Renvoie soit `{ ok: true, session, headers }` à utiliser pour fetch upstream,
 * soit `{ ok: false, response }` à retourner tel quel (401 / 500).
 */
export async function authorizeAndPrepareHeaders(): Promise<ProxyResult> {
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
    // Audit trail côté API : on remonte l'email du back-office user.
    'X-Actor-Id': session.userEmail || `user:${session.userId}`,
  }
  return { ok: true, session, headers }
}

/**
 * Forward une requête vers `/api/admin/assistance/knowledge<path>` côté FastAPI.
 *
 * @param subpath  ex. ``""`` (list/create), ``"/summary"``, ``"/preview-block"``,
 *                 ``"/<slug>"``.
 * @param method   verb HTTP standard.
 * @param body     payload JSON sérialisable (POST/PUT). Ignoré pour GET/DELETE.
 * @param query    paramètres URL à concaténer (déjà encodés ou non).
 */
export async function forwardKnowledgeRequest(
  subpath: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  body?: unknown,
  query?: Record<string, string | undefined | null>,
): Promise<NextResponse> {
  const auth = await authorizeAndPrepareHeaders()
  if (!auth.ok) return auth.response

  const url = new URL(
    buildBackendUrl(`/api/admin/assistance/knowledge${subpath}`),
  )
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
    }
  }

  try {
    const init: RequestInit = {
      method,
      headers: auth.headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    }
    if (body !== undefined && method !== 'GET' && method !== 'DELETE') {
      init.body = JSON.stringify(body)
    }
    const upstream = await fetch(url.toString(), init)

    if (upstream.status === 204) {
      return new NextResponse(null, { status: 204 })
    }

    const text = await upstream.text()
    let json: unknown = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      // Réponse upstream non-JSON → on transmet en clair.
      return new NextResponse(text, {
        status: upstream.status,
        headers: { 'Content-Type': upstream.headers.get('content-type') || 'text/plain' },
      })
    }

    return NextResponse.json(json, { status: upstream.status })
  } catch (error) {
    console.error('[assistance-knowledge-proxy]', subpath, method, error)
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 502 },
    )
  }
}
