import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'
import { buildBackendUrl, getBackendBaseUrl } from '@/lib/backend'

// GET /api/admin/jurisdiction-configs/[id] - Get config by ID
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const url = buildBackendUrl(`/api/jurisdiction-configs/${params.id}`)

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
        const errorBody = await response.json().catch(() => ({ error: 'Failed to fetch config' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 200 })
    } catch (fetchError: any) {
      console.error('Error fetching jurisdiction config:', {
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
    console.error('Error in GET /api/admin/jurisdiction-configs/[id]:', {
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

// PUT /api/admin/jurisdiction-configs/[id] - Update config
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const url = buildBackendUrl(`/api/jurisdiction-configs/${params.id}`)

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
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: 'Failed to update config' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      const data = await response.json()
      return NextResponse.json(data, { status: 200 })
    } catch (fetchError: any) {
      console.error('Error updating jurisdiction config:', {
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
    console.error('Error in PUT /api/admin/jurisdiction-configs/[id]:', {
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

// DELETE /api/admin/jurisdiction-configs/[id] - Delete config
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const url = buildBackendUrl(`/api/jurisdiction-configs/${params.id}`)

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
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({ error: 'Failed to delete config' }))
        return NextResponse.json(errorBody, { status: response.status })
      }

      // DELETE returns 204 No Content, so no body to parse
      return new NextResponse(null, { status: 204 })
    } catch (fetchError: any) {
      console.error('Error deleting jurisdiction config:', {
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
    console.error('Error in DELETE /api/admin/jurisdiction-configs/[id]:', {
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
