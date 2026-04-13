import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { preflightCustodyRequest } from '@/lib/custody-bff'

export async function GET(request: NextRequest) {
  try {
    const pre = preflightCustodyRequest(await getSessionFromCookie())
    if (!pre.ok) return pre.response

    const { searchParams } = new URL(request.url)
    const params = new URLSearchParams()
    for (const [key, val] of searchParams.entries()) params.set(key, val)

    const res = await fetch(
      `${buildBackendUrl('/api/admin/custody/webhook-events')}?${params.toString()}`,
      {
        headers: pre.headers,
      },
    )
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[custody/webhook-events GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
