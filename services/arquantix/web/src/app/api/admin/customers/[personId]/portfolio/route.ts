import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ personId: string }> },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { personId } = await params
    const url = new URL(request.url)
    const txLimit = url.searchParams.get('tx_limit') ?? '100'
    const backendUrl = buildBackendUrl(
      `/api/admin/customers/${encodeURIComponent(personId)}/portfolio?tx_limit=${encodeURIComponent(txLimit)}`,
    )
    const res = await fetch(backendUrl, {
      cache: 'no-store',
      headers: {
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[api/admin/customers/[personId]/portfolio GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
