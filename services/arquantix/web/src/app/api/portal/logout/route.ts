import { NextRequest, NextResponse } from 'next/server'
import { clearPortalSessionCookies } from '@/lib/portal/portalSession'
import { resolvePortalLogoutRedirectPath } from '@/lib/portal/resolvePortalLogoutRedirectPath'

/** Déconnexion navigateur : purge cookies puis redirect relatif (303). */
export async function GET(request: NextRequest) {
  const redirectPath = resolvePortalLogoutRedirectPath(
    request.nextUrl.searchParams.get('redirect'),
  )
  const res = NextResponse.redirect(redirectPath, 303)
  clearPortalSessionCookies(res)
  return res
}

export async function POST() {
  const res = NextResponse.json({ ok: true })
  clearPortalSessionCookies(res)
  return res
}
