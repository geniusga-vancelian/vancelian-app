import { NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function POST() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const res = await portalUpstreamFetch('/api/wallets/solana/create', {
    method: 'POST',
    signal: AbortSignal.timeout(30000),
  })
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    return NextResponse.json(data ?? { error: 'upstream_error' }, { status: res.status })
  }

  return NextResponse.json(data)
}
