import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

    const { searchParams } = new URL(request.url)
    const accountId = searchParams.get('account_id')

    let url: string
    if (accountId) {
      url = buildBackendUrl(`/api/admin/exchange/crypto-custody/${accountId}/history`)
    } else {
      url = buildBackendUrl('/api/admin/exchange/crypto-custody')
    }

    const res = await fetch(url, {
      headers: {
        'X-Actor-Type': 'admin',
        'X-Actor-Id': session.userEmail,
        'X-Actor-Roles': 'admin',
      },
      cache: 'no-store',
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[exchange/crypto-custody GET]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
