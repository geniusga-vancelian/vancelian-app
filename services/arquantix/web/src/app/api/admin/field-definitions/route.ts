import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl, getBackendBaseUrl } from '@/lib/backend'

// GET /api/admin/field-definitions - List all field definitions
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const category = searchParams.get('category')
    const is_active = searchParams.get('is_active')
    const search = searchParams.get('search')

    let url = buildBackendUrl('/api/field-definitions')
    const params = new URLSearchParams()
    if (category) params.append('category', category)
    if (is_active !== null) params.append('is_active', is_active)
    if (search) params.append('search', search)
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
        const errorBody = await response.json().catch(() => ({ error: 'Failed to fetch field definitions' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 200 })
    } catch (fetchError: any) {
      console.error('Error fetching field definitions:', {
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
    console.error('Error in GET /api/admin/field-definitions:', {
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
