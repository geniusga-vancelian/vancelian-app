import { NextRequest, NextResponse } from 'next/server'
import { clearPortalSessionCookies } from '@/lib/portal/portalSession'
import { PORTAL_ROUTES, isPortalAuthPathname } from '@/lib/portal/portalRouting'
import { PORTAL_LOGIN_SIGNED_OUT_PARAM } from '@/lib/portal/navigateToPortalLogin'

function resolveSafeLogoutRedirect(request: NextRequest, redirectParam: string | null): URL {
  const fallback = new URL(PORTAL_ROUTES.login, request.url)
  fallback.searchParams.set(PORTAL_LOGIN_SIGNED_OUT_PARAM, '1')

  if (!redirectParam?.trim()) return fallback

  try {
    const candidate = new URL(redirectParam, request.url)
    if (candidate.origin !== new URL(request.url).origin) return fallback
    if (!isPortalAuthPathname(candidate.pathname)) return fallback
    return candidate
  } catch {
    return fallback
  }
}

/** Déconnexion navigateur : purge cookies puis redirect immédiat (logout perçu instantané). */
export async function GET(request: NextRequest) {
  const redirect = resolveSafeLogoutRedirect(request, request.nextUrl.searchParams.get('redirect'))
  const res = NextResponse.redirect(redirect, 303)
  clearPortalSessionCookies(res)
  return res
}

export async function POST() {
  const res = NextResponse.json({ ok: true })
  clearPortalSessionCookies(res)
  return res
}
