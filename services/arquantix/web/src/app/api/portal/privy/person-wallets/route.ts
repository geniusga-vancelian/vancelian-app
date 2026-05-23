import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import {
  readPortalAccessToken,
  readPortalDeviceIdFromRequest,
} from '@/lib/portal/portalSession'

/** Wallets `person_crypto_wallets` actifs pour la session portail (proxy FastAPI). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const deviceId = readPortalDeviceIdFromRequest(request)

  const res = await fetch(buildBackendUrl('/auth/privy/person-wallets'), {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      'X-Device-ID': deviceId,
    },
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    return NextResponse.json(data ?? { error: 'upstream_error' }, { status: res.status })
  }

  return NextResponse.json(data)
}
