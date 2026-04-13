import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const instrumentId = searchParams.get('instrument_id')
    const start = searchParams.get('start')
    const end = searchParams.get('end')

    if (!instrumentId || !start || !end) {
      return NextResponse.json(
        { error: 'Missing required parameters: instrument_id, start, end' },
        { status: 400 }
      )
    }

    // Validate date format
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/
    if (!dateRegex.test(start) || !dateRegex.test(end)) {
      return NextResponse.json(
        { error: 'Invalid date format. Use YYYY-MM-DD' },
        { status: 400 }
      )
    }

    const backendUrl = buildBackendUrl(`/api/market-data/instruments/${instrumentId}/bars?start=${start}&end=${end}`)

    if (process.env.NODE_ENV === 'development') {
      console.log('[Market Data Bars] Backend URL:', backendUrl)
    }

    try {
      const signed = await signAdminBackendJwtFromSession(session)
      if (!signed.ok) {
        return NextResponse.json(
          { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
          { status: 403 }
        )
      }
      const token = signed.token

      const backendResponse = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        let errorData: { detail?: string; error?: string; message?: string } = {}
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }

        const errorMsg =
          errorData.detail ?? errorData.error ?? errorData.message ?? `Backend request failed (${backendResponse.status})`
        const message = typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)
        return NextResponse.json(
          { error: message, code: 'BACKEND_ERROR', status: backendResponse.status },
          { status: backendResponse.status }
        )
      }

      const result = await backendResponse.json()
      return NextResponse.json(result)
    } catch (error: any) {
      console.error('[Market Data Bars] Backend proxy error:', {
        message: error.message,
        url: backendUrl,
      })

      const isConnectionError =
        error.message?.includes('fetch failed') ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT'

      const errorMsg = isConnectionError
        ? `Backend is unavailable. Please ensure the FastAPI backend is running on ${backendUrl}`
        : (error.message || 'Backend request failed')

      return NextResponse.json(
        {
          error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg),
          code: isConnectionError ? 'BACKEND_UNAVAILABLE' : 'BACKEND_ERROR',
          url: backendUrl,
        },
        { status: 502 }
      )
    }
  } catch (error) {
    console.error('Market Data bars error:', error)
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) },
      { status: 500 }
    )
  }
}






