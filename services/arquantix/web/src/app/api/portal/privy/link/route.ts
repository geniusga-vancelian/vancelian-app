import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'
import {
  readPortalAccessToken,
  readPortalDeviceIdFromRequest,
} from '@/lib/portal/portalSession'

type LinkBody = {
  privy_user_id?: string
  email?: string
}

/** Lie un `privy_user_id` au `person_id` du JWT portail (proxy FastAPI). */
export async function POST(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const body = (await request.json()) as LinkBody
  const privyUserId = body.privy_user_id?.trim()
  if (!privyUserId) {
    return NextResponse.json({ error: 'privy_user_id required' }, { status: 400 })
  }

  const payload: Record<string, string> = { privy_user_id: privyUserId }
  if (body.email?.trim()) {
    payload.email = body.email.trim()
  }

  const res = await fetch(buildBackendUrl('/auth/privy/link'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-Device-ID': readPortalDeviceIdFromRequest(request),
    },
    body: JSON.stringify(payload),
    cache: 'no-store',
    signal: AbortSignal.timeout(15000),
  })

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    return NextResponse.json(data ?? { error: 'upstream_error' }, { status: res.status })
  }

  return NextResponse.json(data)
}
