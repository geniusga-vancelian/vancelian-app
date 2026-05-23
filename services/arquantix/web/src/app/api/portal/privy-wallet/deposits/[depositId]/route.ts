import { NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

type RouteContext = { params: Promise<{ depositId: string }> }

export async function GET(_request: Request, context: RouteContext) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const { depositId } = await context.params
  const res = await portalUpstreamFetch(
    `/api/app/privy-wallet/deposits/${encodeURIComponent(depositId)}`,
    { signal: AbortSignal.timeout(15000) },
  )
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    return NextResponse.json(data ?? { error: 'upstream_error' }, { status: res.status })
  }

  return NextResponse.json(data)
}
