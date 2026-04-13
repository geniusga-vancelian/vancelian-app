import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const res = await fetch(buildBackendUrl('/api/lending/products/admin/pools'), {
      next: { revalidate: 5 },
    })

    if (!res.ok) {
      return NextResponse.json({ pools: [] }, { status: 200 })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ pools: [] })
  }
}
