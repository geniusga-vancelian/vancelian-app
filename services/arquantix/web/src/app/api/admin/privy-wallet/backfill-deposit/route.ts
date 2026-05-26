import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const res = await fetch(buildBackendUrl('/api/admin/privy-wallet/backfill-deposit'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[api/admin/privy-wallet/backfill-deposit POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
