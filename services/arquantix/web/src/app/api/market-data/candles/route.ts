import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session || !session.userEmail) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const { searchParams } = new URL(request.url)
    const instrumentCode = searchParams.get('instrument_code')
    const provider = searchParams.get('provider') || 'binance'
    const start = searchParams.get('start')
    const end = searchParams.get('end')
    const tf = searchParams.get('tf') || '1d'

    if (!instrumentCode) {
      return NextResponse.json({ error: 'instrument_code is required' }, { status: 400 })
    }

    const queryParams = new URLSearchParams({
      instrument_code: instrumentCode,
      provider,
      tf,
    })
    if (start) queryParams.append('start', start)
    if (end) queryParams.append('end', end)

    const backendUrl = buildBackendUrl(`/api/market-data/candles?${queryParams.toString()}`)

    const signed = await signAdminBackendJwtFromSession(session, {
      expiresIn: '1h',
    })
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Backend error' }))
      return NextResponse.json(
        {
          error: errorData.detail || errorData.error || 'Backend request failed',
          backend_status: response.status,
          backend_body: errorData,
        },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Candles fetch error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

