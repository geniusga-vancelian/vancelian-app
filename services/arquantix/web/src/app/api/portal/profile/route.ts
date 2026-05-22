import { NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const res = await portalUpstreamFetch('/api/app/profile', {
    signal: AbortSignal.timeout(15000),
  })
  const profile = await res.json().catch(() => null)

  if (!res.ok) {
    return NextResponse.json(profile ?? { error: 'upstream_error' }, { status: res.status })
  }

  return NextResponse.json({ profile })
}
