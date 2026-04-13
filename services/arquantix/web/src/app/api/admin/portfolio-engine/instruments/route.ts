/**
 * Proxy vers FastAPI pour lister les instruments disponibles (ex. BTC-SPOT, ETH-SPOT).
 * Utilisé par le formulaire de création de Bundle.
 */
import { NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const url = buildBackendUrl('/api/portfolio-engine/instruments?instrument_type=spot&limit=200')
    const res = await fetch(url, { signal: AbortSignal.timeout(10000) })

    if (!res.ok) {
      const body = await res.text()
      return NextResponse.json(
        { error: 'Backend request failed', detail: body },
        { status: res.status },
      )
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('[instruments proxy]', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
