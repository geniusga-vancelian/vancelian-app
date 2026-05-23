import { NextRequest, NextResponse } from 'next/server'
import { clearPortalSessionCookies } from '@/lib/portal/portalSession'
import { resolvePortalLogoutRedirectUrl } from '@/lib/portal/resolvePortalLogoutRedirectPath'

/** Déconnexion navigateur : purge cookies puis redirect absolu (303). */
export async function GET(request: NextRequest) {
  const redirectUrl = resolvePortalLogoutRedirectUrl(
    request,
    request.nextUrl.searchParams.get('redirect'),
  )
  const res = NextResponse.redirect(redirectUrl, 303)
  clearPortalSessionCookies(res)
  return res
}

export async function POST() {
  const res = NextResponse.json({ ok: true })
  clearPortalSessionCookies(res)
  return res
}
