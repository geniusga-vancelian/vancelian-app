import { NextRequest, NextResponse } from 'next/server'
import { buildBackendUrl } from '@/lib/backend'

// GET /api/market-data/market-summary?symbols=BTCUSDT,ETHUSDT
// Proxy vers le backend (endpoint public, pas d'auth).
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const symbols = searchParams.get('symbols')
    if (!symbols || !symbols.trim()) {
      return NextResponse.json(
        { error: 'Missing required parameter: symbols' },
        { status: 400 }
      )
    }
    const backendUrl = buildBackendUrl(`/api/market-data/market-summary?symbols=${encodeURIComponent(symbols.trim())}`)
    const response = await fetch(backendUrl, { cache: 'no-store' })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      return NextResponse.json(err, { status: response.status })
    }
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[market-summary] Error:', error)
    return NextResponse.json({ error: error.message || 'Internal server error' }, { status: 500 })
  }
}
