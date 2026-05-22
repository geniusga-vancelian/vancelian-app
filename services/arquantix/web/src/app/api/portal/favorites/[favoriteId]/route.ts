import { NextResponse } from 'next/server'
import { portalUpstreamFetch } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export async function DELETE(
  _request: Request,
  { params }: { params: { favoriteId: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const favoriteId = params.favoriteId?.trim()
  if (!favoriteId) {
    return NextResponse.json({ error: 'Invalid favorite id' }, { status: 400 })
  }

  const res = await portalUpstreamFetch(`/api/app/favorites/${encodeURIComponent(favoriteId)}`, {
    method: 'DELETE',
  })
  if (res.status === 204) {
    return new NextResponse(null, { status: 204 })
  }
  const data = await res.json().catch(() => null)
  return NextResponse.json(data, { status: res.status })
}
