import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl, getBackendBaseUrl } from '@/lib/backend'

// POST /api/admin/jurisdiction-configs/[id]/publish - Publish config
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const url = buildBackendUrl(`/api/jurisdiction-configs/${params.id}/publish`)

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
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: 'Failed to publish config' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 200 })
    } catch (fetchError: any) {
      console.error('Error publishing jurisdiction config:', {
        error: fetchError.message,
        url,
        backendUrl: getBackendBaseUrl(),
        configId: params.id,
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
    console.error('Error in POST /api/admin/jurisdiction-configs/[id]/publish:', {
      error: error.message,
      stack: error.stack,
      backendUrl: getBackendBaseUrl(),
      configId: params.id,
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
