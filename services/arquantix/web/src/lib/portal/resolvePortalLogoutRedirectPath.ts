import type { NextRequest } from 'next/server'
import { PORTAL_ROUTES, isPortalAuthPathname } from '@/lib/portal/portalRouting'

const PORTAL_LOGIN_SIGNED_OUT_PARAM = 'signed_out' as const

/** Chemin login post sign-out (relatif — conserve l’hôte public du navigateur). */
export function portalLogoutRedirectPathFallback(): string {
  return `${PORTAL_ROUTES.login}?${PORTAL_LOGIN_SIGNED_OUT_PARAM}=1`
}

/**
 * Valide le paramètre `redirect` et renvoie un chemin relatif sûr.
 * Ne jamais construire d’URL absolue via `request.url` en prod ECS (HOSTNAME=0.0.0.0).
 */
export function resolvePortalLogoutRedirectPath(redirectParam: string | null | undefined): string {
  const fallback = portalLogoutRedirectPathFallback()
  const raw = redirectParam?.trim()
  if (!raw) return fallback

  // Uniquement chemins relatifs same-site (évite open redirect).
  if (!raw.startsWith('/') || raw.startsWith('//')) return fallback

  try {
    const candidate = new URL(raw, 'http://localhost')
    if (!isPortalAuthPathname(candidate.pathname)) return fallback
    return `${candidate.pathname}${candidate.search}`
  } catch {
    return fallback
  }
}

/** Construit une URL absolue sûre pour `NextResponse.redirect` (Next.js exige une URL absolue). */
export function resolvePortalLogoutRedirectUrl(
  request: Pick<NextRequest, 'headers' | 'nextUrl'>,
  redirectParam: string | null | undefined,
): string {
  const path = resolvePortalLogoutRedirectPath(redirectParam)
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host')
  if (host) {
    const proto =
      request.headers.get('x-forwarded-proto') ??
      (host.startsWith('localhost') || host.startsWith('127.0.0.1') ? 'http' : 'https')
    return `${proto}://${host}${path}`
  }
  return new URL(path, request.nextUrl.origin).toString()
}
