import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

/** GET /api/market-data/chart-history?symbol=BTCUSDT&period=1j */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const symbol = searchParams.get('symbol')?.trim().toUpperCase()
    const period = searchParams.get('period')?.trim()
    if (!symbol || !period) {
      return NextResponse.json(
        { error: 'Missing required parameters: symbol, period' },
        { status: 400 },
      )
    }
    const backendUrl = buildBackendUrl(
      `/api/market-data/chart-history?symbol=${encodeURIComponent(symbol)}&period=${encodeURIComponent(period)}`,
    )
    const response = await fetch(backendUrl, { cache: 'no-store' })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      return NextResponse.json(err, { status: response.status })
    }
    return NextResponse.json(await response.json())
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Internal server error'
    console.error('[chart-history] Error:', error)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
