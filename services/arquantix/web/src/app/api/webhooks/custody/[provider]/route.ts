import { NextRequest, NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> },
) {
  try {
    const { provider } = await params
    const body = await request.json()
    const res = await fetch(
      buildBackendUrl(`/api/webhooks/custody/${provider}`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    )
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (error) {
    console.error('[webhooks/custody POST]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
