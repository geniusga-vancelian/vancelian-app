import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

const ALLOWED_ACTIONS = new Set([
  'open-fundraising',
  'activate',
  'mark-repaid',
  'close',
])

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ productId: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { productId } = await params
    const { action } = await request.json()

    if (!action || !ALLOWED_ACTIONS.has(action)) {
      return NextResponse.json(
        { detail: `Invalid action: ${action}. Allowed: ${[...ALLOWED_ACTIONS].join(', ')}` },
        { status: 400 }
      )
    }

    const url = buildBackendUrl(`/api/lending/products/${productId}/${action}`)
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })

    const text = await res.text()
    let data: Record<string, unknown>
    try {
      data = JSON.parse(text)
    } catch {
      console.error(`[lending/products/transition] Non-JSON response:`, text.slice(0, 500))
      return NextResponse.json({ detail: 'Backend returned non-JSON response' }, { status: 502 })
    }

    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[lending/products/transition] Error:', error)
    return NextResponse.json(
      { detail: 'Backend unavailable' },
      { status: 502 }
    )
  }
}
