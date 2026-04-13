import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

    const res = await fetch(buildBackendUrl('/api/admin/exchange/context'), {
      headers: {
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
      cache: 'no-store',
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[exchange/context GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
