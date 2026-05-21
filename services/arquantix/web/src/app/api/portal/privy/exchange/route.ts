import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import {
  ensurePortalDeviceIdCookie,
  readPortalDeviceIdFromRequest,
  type PortalSessionPayload,
  applyPortalSessionCookies,
} from '@/lib/portal/portalSession'

type ExchangeBody = {
  privy_access_token?: string
  privy_identity_token?: string
  signUpMode?: boolean
  email?: string
}

function parseExchangeResponse(data: unknown): PortalSessionPayload | null {
  if (!data || typeof data !== 'object') return null
  const row = data as Record<string, unknown>
  const accessToken =
    typeof row.access_token === 'string'
      ? row.access_token
      : typeof row.accessToken === 'string'
        ? row.accessToken
        : null
  if (!accessToken) return null
  return {
    accessToken,
    refreshToken:
      typeof row.refresh_token === 'string'
        ? row.refresh_token
        : typeof row.refreshToken === 'string'
          ? row.refreshToken
          : null,
    personId: typeof row.person_id === 'string' ? row.person_id : null,
    peClientId: typeof row.pe_client_id === 'string' ? row.pe_client_id : null,
  }
}

/** Échange jeton Privy → session JWT Vancelian (même endpoint que Flutter). */
export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as ExchangeBody
    const privyToken = body.privy_access_token?.trim()
    if (!privyToken) {
      return NextResponse.json({ error: 'privy_access_token required' }, { status: 400 })
    }

    const deviceId = readPortalDeviceIdFromRequest(request)
    const path = body.signUpMode ? '/auth/signup/privy/exchange' : '/auth/privy/exchange'
    const payload: Record<string, string> = { privy_access_token: privyToken }
    const identityToken = body.privy_identity_token?.trim()
    if (identityToken) {
      payload.privy_identity_token = identityToken
    }
    if (body.signUpMode && body.email?.trim()) {
      payload.email = body.email.trim()
    }

    const upstream = await fetch(buildBackendUrl(path), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'X-Device-ID': deviceId,
      },
      body: JSON.stringify(payload),
      cache: 'no-store',
    })

    const data = await upstream.json().catch(() => null)
    if (!upstream.ok) {
      return NextResponse.json(data ?? { error: 'exchange_failed' }, { status: upstream.status })
    }

    const session = parseExchangeResponse(data)
    if (!session) {
      return NextResponse.json({ error: 'invalid_exchange_response' }, { status: 502 })
    }

    const res = NextResponse.json({
      ok: true,
      personId: session.personId,
      peClientId: session.peClientId,
    })
    applyPortalSessionCookies(res, session)
    ensurePortalDeviceIdCookie(res, deviceId)
    return res
  } catch (error) {
    console.error('[api/portal/privy/exchange]', error)
    return NextResponse.json({ error: 'internal_error' }, { status: 500 })
  }
}
