import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { preflightCustodyRequest } from '@/lib/custody-bff'

export async function POST(request: NextRequest) {
  try {
    const pre = preflightCustodyRequest(await getSessionFromCookie())
    if (!pre.ok) return pre.response

    const { searchParams } = new URL(request.url)
    const dryRun = searchParams.get('dry_run') === 'true'
    const url = buildBackendUrl(
      `/api/admin/custody/reset-financial-test-state?dry_run=${dryRun}`,
    )
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...pre.headers,
      },
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[custody/reset-financial-test-state POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
