import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ poolId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { poolId } = await params

    const res = await fetch(buildBackendUrl(`/api/lending/products/admin/pools/${poolId}`))

    if (!res.ok) {
      return NextResponse.json({ error: 'Pool not found' }, { status: res.status })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
