import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { preflightCustodyRequest } from '@/lib/custody-bff'

export async function POST(request: NextRequest) {
  try {
    const pre = preflightCustodyRequest(await getSessionFromCookie())
    if (!pre.ok) return pre.response

    const body = await request.json()
    const res = await fetch(buildBackendUrl('/api/admin/custody/simulate-withdrawal'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...pre.headers,
      },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[custody/simulate-withdrawal POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
