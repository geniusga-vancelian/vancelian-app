import { buildBackendUrl } from '@/lib/backend'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

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
