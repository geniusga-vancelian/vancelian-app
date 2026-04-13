import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const q = searchParams.get('q') ?? ''
    const limit = searchParams.get('limit') ?? '20'

    const qs = new URLSearchParams()
    qs.set('q', q)
    qs.set('limit', limit)

    const url = `${buildBackendUrl('/api/admin/customers/search')}?${qs.toString()}`
    const res = await fetch(url, {
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
    console.error('[api/admin/customers/search GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
