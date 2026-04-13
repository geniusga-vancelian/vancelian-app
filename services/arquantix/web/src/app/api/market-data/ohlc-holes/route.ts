import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

// GET /api/market-data/ohlc-holes?instrument_ids=1,2,3 (optionnel; si absent = tous les crypto Binance)
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const instrument_ids = searchParams.get('instrument_ids')
    const params = new URLSearchParams()
    if (instrument_ids?.trim()) params.set('instrument_ids', instrument_ids.trim())
    const queryString = params.toString()
    const url = buildBackendUrl(`/api/market-data/ohlc-holes${queryString ? `?${queryString}` : ''}`)

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to fetch OHLC holes' }))
      return NextResponse.json(error, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[ohlc-holes] Error:', error)
    return NextResponse.json({ error: error.message || 'Internal server error' }, { status: 500 })
  }
}
