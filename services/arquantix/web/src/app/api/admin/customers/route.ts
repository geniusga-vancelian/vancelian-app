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
    const page = searchParams.get('page') ?? '1'
    const page_size = searchParams.get('page_size') ?? '25'
    const q = searchParams.get('q') ?? ''
    const sort = searchParams.get('sort') ?? '-updated_at'
    const country = searchParams.get('country') ?? ''

    const qs = new URLSearchParams()
    qs.set('page', page)
    qs.set('page_size', page_size)
    if (q) qs.set('q', q)
    qs.set('sort', sort)
    if (country) qs.set('country', country)

    const url = `${buildBackendUrl('/api/admin/customers')}?${qs.toString()}`
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
    console.error('[api/admin/customers GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
