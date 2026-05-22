import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

/** Proxy public vers FastAPI top-movers (aligné Flutter Markets). */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '10'
    const backendUrl = buildBackendUrl(
      `/api/market-data/top-movers?limit=${encodeURIComponent(limit)}`,
    )
    const response = await fetch(backendUrl, { cache: 'no-store' })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      return NextResponse.json(err, { status: response.status })
    }
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Internal server error'
    console.error('[market-data/top-movers]', error)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
