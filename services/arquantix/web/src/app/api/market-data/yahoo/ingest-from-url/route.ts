import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function POST(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session || !session.userEmail) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const body = await request.json()
    
    const backendUrl = buildBackendUrl('/api/market-data/yahoo/ingest-from-url')
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
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    // Parse JSON response (FastAPI always returns JSON)
    const data = await response.json()

    if (!response.ok) {
      // Preserve backend status code and response body for better error handling
      return NextResponse.json(
        {
          error: 'Backend request failed',
          backend_status: response.status,
          backend_body: data,
        },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Yahoo ingest from URL error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

