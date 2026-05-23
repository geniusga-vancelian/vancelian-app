import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import {
  ensurePortalDeviceIdCookie,
  readPortalDeviceIdFromRequest,
  type PortalSessionPayload,
  applyPortalSessionCookies,
} from '@/lib/portal/portalSession'
import { isUpstreamExchangeUnavailable } from '@/lib/portal/parsePortalExchangeError'

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
    if (body.email?.trim()) {
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

    const raw = await upstream.text()
    let data: unknown = null
    if (raw.trim()) {
      try {
        data = JSON.parse(raw)
      } catch {
        console.error('[api/portal/privy/exchange] non-json upstream', {
          status: upstream.status,
          bodyPreview: raw.slice(0, 240),
        })
      }
    }
    if (!upstream.ok) {
      if (data && typeof data === 'object') {
        return NextResponse.json(data, { status: upstream.status })
      }
      return NextResponse.json(
        {
          error: 'exchange_failed',
          message:
            upstream.status >= 502
              ? 'Le service d’authentification est temporairement indisponible. Réessayez dans quelques secondes.'
              : 'Échange de session impossible. Réessayez.',
        },
        { status: upstream.status >= 502 ? 502 : upstream.status || 502 },
      )
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
    const upstreamDown = isUpstreamExchangeUnavailable(error)
    return NextResponse.json(
      {
        error: 'exchange_failed',
        message: upstreamDown
          ? 'Le service d’authentification est temporairement indisponible. Réessayez dans quelques secondes.'
          : 'Échange de session impossible. Réessayez.',
      },
      { status: upstreamDown ? 502 : 500 },
    )
  }
}
