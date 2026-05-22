import { NextRequest, NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const qs = request.nextUrl.searchParams.toString()
  const path = qs ? `/api/app/favorites?${qs}` : '/api/app/favorites'
  const res = await portalUpstreamFetch(path)
  const data = await res.json().catch(() => null)
  return NextResponse.json(data, { status: res.status })
}

export async function POST(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const body = await request.json().catch(() => null)
  const res = await portalUpstreamFetch('/api/app/favorites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  return NextResponse.json(data, { status: res.status })
}
