import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const validateSchema = z.object({
  jurisdiction: z.string().min(1),
  purpose: z.enum(['KYC', 'AML_RISK']),
  spec: z.any(),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { jurisdiction, purpose, spec } = validateSchema.parse(body)

    const backendUrl = buildBackendUrl('/api/ai/jurisdiction-configs/validate')

    const signed = await signAdminBackendJwtFromSession(session)
    if (!signed.ok) {
      return NextResponse.json(
        { error: "Cette action n'est pas disponible avec votre compte ou la configuration du serveur est incomplète. Contactez un administrateur." },
        { status: 403 }
      )
    }
    const token = signed.token

    try {
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          jurisdiction,
          purpose,
          spec,
        }),
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }

        const errorMsg =
          errorData.detail || errorData.error || errorData.message || `Backend request failed (${response.status})`
        const errorMessage = typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)

        return NextResponse.json(
          {
            error: errorMessage,
            code: 'BACKEND_ERROR',
            status: response.status,
          },
          { status: response.status }
        )
      }

      const result = await response.json()
      return NextResponse.json(result)
    } catch (fetchError: any) {
      console.error('[AI Jurisdiction Configs Validate] Backend proxy error:', {
        message: fetchError.message,
        url: backendUrl,
      })

      const isConnectionError =
        fetchError.message?.includes('fetch failed') ||
        fetchError.code === 'ECONNREFUSED' ||
        fetchError.code === 'ECONNRESET' ||
        fetchError.code === 'ETIMEDOUT'

      const errorMsg = isConnectionError
        ? `Backend is unavailable. Please ensure the FastAPI backend is running on ${backendUrl}`
        : fetchError.message || 'Backend request failed'

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
    console.error('AI Jurisdiction Configs validate error:', error)
    if (error instanceof z.ZodError) {
      const detailsStr = error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join(', ')
      return NextResponse.json({ error: 'Invalid request data', details: detailsStr }, { status: 400 })
    }
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) }, { status: 500 })
  }
}
