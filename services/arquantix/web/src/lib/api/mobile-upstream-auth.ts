/**
 * Propage `Authorization: Bearer …` du client (Flutter → BFF Next.js) vers l’API Python.
 * Sans en-tête, le backend peut encore résoudre le client « test » Flutter (dev uniquement).
 */
export function upstreamHeadersWithAuth(
  request: Request,
  base?: HeadersInit,
): Headers {
  const headers = new Headers(base ?? undefined)
  const auth = request.headers.get('authorization')
  if (auth?.trim()) {
    headers.set('Authorization', auth)
  }
  return headers
}

/** POST/PATCH JSON vers l’API Python avec Bearer propagé. */
export function jsonHeadersWithUpstreamAuth(request: Request): Headers {
  return upstreamHeadersWithAuth(request, { 'Content-Type': 'application/json' })
}
