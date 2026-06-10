import { buildBackendUrl } from '@/lib/backend'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/**
 * Origine pour les appels BFF → routes `/api/*` du même process Next.
 * En prod ECS, évite le hairpin `https://app.*` (ssl3_get_record:wrong version number).
 */
export function resolvePortalBffOrigin(requestOrigin?: string): string {
  const explicit = process.env.PORTAL_INTERNAL_ORIGIN?.trim()
  if (explicit) return explicit.replace(/\/$/, '')

  if (process.env.NODE_ENV === 'production') {
    const port = process.env.PORT?.trim() || '3000'
    return `http://127.0.0.1:${port}`
  }

  const fallback = requestOrigin?.trim() || `http://127.0.0.1:${process.env.PORT?.trim() || '3000'}`
  return fallback.replace(/\/$/, '')
}

/** Appel BFF mobile upstream avec le JWT portail (cookie httpOnly). */
export async function portalUpstreamFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const token = await readPortalAccessToken()
  const headers = new Headers(init?.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  headers.set('Accept', 'application/json')
  return fetch(buildBackendUrl(path), {
    ...init,
    headers,
    cache: 'no-store',
  })
}

/** Parse une réponse upstream en JSON — évite les erreurs opaques si le gateway renvoie du HTML. */
export async function parsePortalUpstreamJson(
  res: Response,
): Promise<{ data: unknown; parseError: string | null }> {
  const text = await res.text()
  const contentType = res.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    const snippet = text.replace(/\s+/g, ' ').trim().slice(0, 160)
    return {
      data: {
        error: 'upstream_non_json',
        upstream_status: res.status,
        detail: snippet || 'empty response',
      },
      parseError: snippet || 'empty response',
    }
  }
  try {
    return { data: JSON.parse(text) as unknown, parseError: null }
  } catch {
    const snippet = text.replace(/\s+/g, ' ').trim().slice(0, 160)
    return {
      data: {
        error: 'upstream_invalid_json',
        upstream_status: res.status,
        detail: snippet || 'invalid json',
      },
      parseError: snippet || 'invalid json',
    }
  }
}
