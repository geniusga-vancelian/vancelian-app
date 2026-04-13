import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

// GET /api/market-data/instruments - List instruments
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const is_active = searchParams.get('is_active')
    const asset_class = searchParams.get('asset_class')
    const provider = searchParams.get('provider')

    const params = new URLSearchParams()
    if (is_active) params.set('is_active', is_active)
    if (asset_class) params.set('asset_class', asset_class)
    if (provider) params.set('provider', provider)
    const queryString = params.toString()
    const url = buildBackendUrl(`/api/market-data/instruments${queryString ? `?${queryString}` : ''}`)

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to fetch instruments' }))
      return NextResponse.json(error, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Error fetching instruments:', error)
    return NextResponse.json({ error: error.message || 'Internal server error' }, { status: 500 })
  }
}
