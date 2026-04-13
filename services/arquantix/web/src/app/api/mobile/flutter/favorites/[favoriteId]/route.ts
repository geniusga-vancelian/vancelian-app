import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { jsonHeadersWithUpstreamAuth, upstreamHeadersWithAuth } from '@/lib/api/mobile-upstream-auth'

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ favoriteId: string }> },
) {
  try {
    const { favoriteId } = await params
    const url = buildBackendUrl(`/api/app/favorites/${favoriteId}`)
    const res = await fetch(url, {
      headers: upstreamHeadersWithAuth(_req),
      method: 'DELETE',
      signal: AbortSignal.timeout(5000),
    })
    if (res.status === 204) return new NextResponse(null, { status: 204 })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/mobile/flutter/favorites/[id] DELETE]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
