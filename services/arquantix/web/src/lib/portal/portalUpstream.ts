import { buildBackendUrl } from '@/lib/backend'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/** Aligné sur markets BFF — 15s provoquait des timeouts prod sur dashboard / crypto. */
export const PORTAL_UPSTREAM_DEFAULT_TIMEOUT_MS = 30_000
export const PORTAL_UPSTREAM_HEAVY_TIMEOUT_MS = 45_000

export type PortalUpstreamJsonResult = { ok: boolean; data: unknown }

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

/** GET upstream JSON — timeout + erreurs réseau → `{ ok: false }` (ne fait pas échouer Promise.all). */
export async function fetchPortalUpstreamJsonSafe(
  path: string,
  options?: { timeoutMs?: number },
): Promise<PortalUpstreamJsonResult> {
  try {
    const res = await portalUpstreamFetch(path, {
      signal: AbortSignal.timeout(options?.timeoutMs ?? PORTAL_UPSTREAM_DEFAULT_TIMEOUT_MS),
    })
    const data = await res.json().catch(() => null)
    return { ok: res.ok, data }
  } catch {
    return { ok: false, data: null }
  }
}

/** GET backend JSON (market-data, etc.) — même sémantique fail-soft que fetchPortalUpstreamJsonSafe. */
export async function fetchPortalBackendJsonSafe(
  path: string,
  options?: { timeoutMs?: number },
): Promise<PortalUpstreamJsonResult> {
  try {
    const res = await fetch(buildBackendUrl(path), {
      cache: 'no-store',
      signal: AbortSignal.timeout(options?.timeoutMs ?? PORTAL_UPSTREAM_DEFAULT_TIMEOUT_MS),
    })
    const data = await res.json().catch(() => null)
    return { ok: res.ok, data }
  } catch {
    return { ok: false, data: null }
  }
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
