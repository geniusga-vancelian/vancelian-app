import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { preflightCustodyRequest } from '@/lib/custody-bff'

export async function GET(request: NextRequest) {
  try {
    const pre = preflightCustodyRequest(await getSessionFromCookie())
    if (!pre.ok) return pre.response

    const { searchParams } = new URL(request.url)
    const skip = searchParams.get('skip') ?? '0'
    const limit = searchParams.get('limit') ?? '50'

    const res = await fetch(
      `${buildBackendUrl('/api/admin/custody/balances')}?skip=${skip}&limit=${limit}`,
      {
        headers: pre.headers,
      },
    )
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[custody/balances GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
