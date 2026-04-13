import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

    const res = await fetch(buildBackendUrl('/api/admin/exchange/run-settlement'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
      cache: 'no-store',
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[exchange/run-settlement POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
