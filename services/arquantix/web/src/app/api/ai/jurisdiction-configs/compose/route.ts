import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const composeSchema = z.object({
  jurisdiction: z.string().min(1, 'Jurisdiction is required and cannot be empty'),
  purpose: z.enum(['KYC', 'AML_RISK'], {
    message: 'Purpose must be either KYC or AML_RISK',
  }),
  prompt: z.string().min(1, 'Prompt is required').max(2000, 'Prompt must be 2000 characters or less'),
  previous_spec: z.any().optional().nullable(),
  messages: z
    .array(z.object({ role: z.string(), content: z.string() }))
    .optional()
    .nullable(),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    
    // Debug log in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[AI Jurisdiction Configs Compose] Request body:', {
        jurisdiction: body.jurisdiction,
        purpose: body.purpose,
        prompt_length: body.prompt?.length,
        has_previous_spec: !!body.previous_spec,
        messages_count: body.messages?.length,
      })
    }
    
    // Normalize empty strings to undefined for optional fields
    if (body.previous_spec === null || body.previous_spec === '') {
      body.previous_spec = undefined
    }
    if (body.messages === null || (Array.isArray(body.messages) && body.messages.length === 0)) {
      body.messages = undefined
    }
    
    const { jurisdiction, purpose, prompt, previous_spec, messages } = composeSchema.parse(body)

    const backendUrl = buildBackendUrl('/api/ai/jurisdiction-configs/compose')

    if (process.env.NODE_ENV === 'development') {
      console.log('[AI Jurisdiction Configs Compose] Proxying to:', backendUrl)
    }

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
          prompt,
          previous_spec: previous_spec || undefined,
          messages: messages || undefined,
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
      console.error('[AI Jurisdiction Configs Compose] Backend proxy error:', {
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
    console.error('AI Jurisdiction Configs compose error:', error)
    if (error instanceof z.ZodError) {
      const details = error.issues.map((issue) => ({
        field: issue.path.join('.'),
        message: issue.message,
        code: issue.code,
      }))
      const detailsStr = details.map((d) => `${d.field}: ${d.message}`).join(', ')
      console.error('Validation errors:', details)
      return NextResponse.json(
        {
          error: 'Invalid request data',
          details: detailsStr,
          validation_errors: details,
        },
        { status: 400 }
      )
    }
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) }, { status: 500 })
  }
}
