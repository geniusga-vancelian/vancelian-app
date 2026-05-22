import { NextRequest, NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function PATCH(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const body = await request.json().catch(() => null)
  const res = await portalUpstreamFetch('/api/app/profile/reference-currency', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  })
  const data = await res.json().catch(() => null)
  return NextResponse.json(data ?? { error: 'upstream_error' }, { status: res.status })
}
