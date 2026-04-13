import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { preflightCustodyRequest } from '@/lib/custody-bff'

export async function GET(request: NextRequest) {
  try {
    const pre = preflightCustodyRequest(await getSessionFromCookie())
    if (!pre.ok) return pre.response

    const { searchParams } = new URL(request.url)
    const qs = searchParams.toString()
    const url = `${buildBackendUrl('/api/admin/custody/accounts')}${qs ? `?${qs}` : ''}`

    const res = await fetch(url, {
      headers: pre.headers,
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[custody/accounts GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
