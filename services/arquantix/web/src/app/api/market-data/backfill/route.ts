import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { z } from 'zod'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const backfillSchema = z.object({
  instrument_id: z.number().int().positive(),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { instrument_id, start_date, end_date } = backfillSchema.parse(body)

    const backendUrl = buildBackendUrl(`/api/market-data/instruments/${instrument_id}/backfill`)

    if (process.env.NODE_ENV === 'development') {
      console.log('[Market Data Backfill] Backend URL:', backendUrl)
      console.log('[Market Data Backfill] Request:', { instrument_id, start_date, end_date })
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
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          start_date,
          end_date,
        }),
      })

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }

        const errorMsg = errorData.detail || errorData.error || errorData.message || `Backend request failed (${backendResponse.status})`
        return NextResponse.json(
          {
            error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg),
            code: 'BACKEND_ERROR',
            status: backendResponse.status,
          },
          { status: backendResponse.status }
        )
      }

      const result = await backendResponse.json()
      return NextResponse.json(result)
    } catch (error: any) {
      console.error('[Market Data Backfill] Backend proxy error:', {
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
    console.error('Market Data backfill error:', error)
    if (error instanceof z.ZodError) {
      const detailsStr = error.issues.map(issue => `${issue.path.join('.')}: ${issue.message}`).join(', ')
      return NextResponse.json(
        { error: 'Invalid request data', details: detailsStr },
        { status: 400 }
      )
    }
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) },
      { status: 500 }
    )
  }
}






