import { cookies } from 'next/headers'
import type { NextRequest, NextResponse } from 'next/server'

export const PORTAL_ACCESS_COOKIE = 'arq_portal_access_token' as const
export const PORTAL_REFRESH_COOKIE = 'arq_portal_refresh_token' as const
export const PORTAL_DEVICE_ID_COOKIE = 'arq_portal_device_id' as const

const PORTAL_COOKIE_MAX_AGE_SEC = 60 * 60 * 24 * 30 // 30 jours

export type PortalSessionPayload = {
  accessToken: string
  refreshToken?: string | null
  personId?: string | null
  peClientId?: string | null
}

export function portalCookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge: PORTAL_COOKIE_MAX_AGE_SEC,
  }
}

export function applyPortalSessionCookies(
  res: NextResponse,
  session: PortalSessionPayload,
): NextResponse {
  res.cookies.set(PORTAL_ACCESS_COOKIE, session.accessToken, portalCookieOptions())
  if (session.refreshToken?.trim()) {
    res.cookies.set(PORTAL_REFRESH_COOKIE, session.refreshToken.trim(), portalCookieOptions())
  }
  return res
}

export function clearPortalSessionCookies(res: NextResponse): NextResponse {
  const clear = { path: '/', maxAge: 0 }
  res.cookies.set(PORTAL_ACCESS_COOKIE, '', clear)
  res.cookies.set(PORTAL_REFRESH_COOKIE, '', clear)
  return res
}

export async function readPortalAccessToken(): Promise<string | null> {
  const store = await cookies()
  return store.get(PORTAL_ACCESS_COOKIE)?.value?.trim() || null
}

export function readPortalAccessTokenFromRequest(request: NextRequest): string | null {
  return request.cookies.get(PORTAL_ACCESS_COOKIE)?.value?.trim() || null
}

export function readPortalDeviceIdFromRequest(request: NextRequest): string {
  const existing = request.cookies.get(PORTAL_DEVICE_ID_COOKIE)?.value?.trim()
  if (existing) return existing
  return crypto.randomUUID()
}

export function ensurePortalDeviceIdCookie(
  res: NextResponse,
  deviceId: string,
): NextResponse {
  if (!deviceId.trim()) return res
  res.cookies.set(PORTAL_DEVICE_ID_COOKIE, deviceId.trim(), {
    ...portalCookieOptions(),
    maxAge: 60 * 60 * 24 * 365,
  })
  return res
}
