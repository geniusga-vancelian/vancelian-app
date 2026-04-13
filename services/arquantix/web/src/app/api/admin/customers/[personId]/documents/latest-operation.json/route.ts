import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ personId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { personId } = await params
    const url = buildBackendUrl(
      `/api/admin/customers/${encodeURIComponent(personId)}/documents/latest-operation.json`
    )
    const res = await fetch(url, {
      cache: 'no-store',
      signal: AbortSignal.timeout(120_000),
      headers: {
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
    })

    const buf = await res.arrayBuffer()
    const upstreamType = res.headers.get('content-type')
    const contentType =
      upstreamType && upstreamType.trim().length > 0
        ? upstreamType
        : res.ok
          ? 'application/json; charset=utf-8'
          : 'application/json; charset=utf-8'

    return new NextResponse(buf, {
      status: res.status,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'no-store',
      },
    })
  } catch (error) {
    console.error('[api/admin/.../latest-operation.json GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
