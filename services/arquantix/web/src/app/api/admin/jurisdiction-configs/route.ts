import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl, getBackendBaseUrl } from '@/lib/backend'

// GET /api/admin/jurisdiction-configs - List all configs
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const jurisdiction = searchParams.get('jurisdiction')
    const purpose = searchParams.get('purpose')
    const status = searchParams.get('status')

    let url = buildBackendUrl('/api/jurisdiction-configs')
    const params = new URLSearchParams()
    if (jurisdiction) params.append('jurisdiction', jurisdiction)
    if (purpose) params.append('purpose', purpose)
    if (status) params.append('status', status)
    if (params.toString()) url += '?' + params.toString()

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: 'Failed to fetch configs' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 200 })
    } catch (fetchError: any) {
      console.error('Error fetching jurisdiction configs:', {
        error: fetchError.message,
        url,
        backendUrl: getBackendBaseUrl(),
      })
      return NextResponse.json(
        {
          error: 'Backend request failed',
          detail: fetchError.message,
        },
        { status: 500 }
      )
    }
  } catch (error: any) {
    console.error('Error in GET /api/admin/jurisdiction-configs:', {
      error: error.message,
      stack: error.stack,
      backendUrl: getBackendBaseUrl(),
    })
    return NextResponse.json(
      {
        error: 'Internal server error',
        detail: error.message,
      },
      { status: 500 }
    )
  }
}

// POST /api/admin/jurisdiction-configs - Create new config
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const url = buildBackendUrl('/api/jurisdiction-configs')

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: 'Failed to create config' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 201 })
    } catch (fetchError: any) {
      console.error('Error creating jurisdiction config:', {
        error: fetchError.message,
        url,
        backendUrl: getBackendBaseUrl(),
      })
      return NextResponse.json(
        {
          error: 'Backend request failed',
          detail: fetchError.message,
        },
        { status: 500 }
      )
    }
  } catch (error: any) {
    console.error('Error in POST /api/admin/jurisdiction-configs:', {
      error: error.message,
      stack: error.stack,
      backendUrl: getBackendBaseUrl(),
    })
    return NextResponse.json(
      {
        error: 'Internal server error',
        detail: error.message,
      },
      { status: 500 }
    )
  }
}
