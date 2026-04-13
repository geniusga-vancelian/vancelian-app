import { NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ personId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { personId } = await params
    const url = buildBackendUrl(`/api/admin/customers/${encodeURIComponent(personId)}/freeze`)
    const res = await fetch(url, {
      method: 'POST',
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
    console.error('[api/admin/customers/[personId]/freeze POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
