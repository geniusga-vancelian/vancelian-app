import { NextRequest, NextResponse } from 'next/server'

import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

async function proxyAdminPost(path: string, body: unknown) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const res = await fetch(buildBackendUrl(path), {
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
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    return proxyAdminPost('/api/admin/privy-wallet/reconciliation/run', body)
  } catch (error) {
    console.error('[api/admin/privy-wallet/reconciliation/run POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
