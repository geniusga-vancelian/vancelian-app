import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const composeEmailUGGSchema = z.object({
  prompt: z.string().min(1).max(2000),
  locale: z.string().regex(/^[a-z]{2}$/).optional().default('en'),
  previous_spec: z.any().optional(), // EmailSpecUGG, validated later
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { prompt, locale, previous_spec } = composeEmailUGGSchema.parse(body)

    // Proxy to FastAPI backend
    const backendUrl = buildBackendUrl('/api/ai/email/compose-ugg')
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[AI Email Compose UGG] Backend URL:', backendUrl)
      console.log('[AI Email Compose UGG] Request body:', {
        prompt: prompt.substring(0, 100) + '...',
        locale,
        hasPreviousSpec: !!previous_spec,
      })
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
          prompt,
          locale: locale || 'en',
          previous_spec: previous_spec || undefined,
        }),
      })

      if (process.env.NODE_ENV === 'development') {
        console.log('[AI Email Compose UGG] Backend response status:', backendResponse.status, backendResponse.statusText)
      }

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }
        console.error('[AI Email Compose UGG] Backend error response:', {
          status: backendResponse.status,
          statusText: backendResponse.statusText,
          url: backendUrl,
          error: errorData
        })
        
        const errorMsg = errorData.detail || errorData.error || errorData.message || `Backend request failed (${backendResponse.status})`
        const errorMessage = typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)
        
        return NextResponse.json(
          {
            error: errorMessage,
            code: 'BACKEND_ERROR',
            status: backendResponse.status,
          },
          { status: backendResponse.status }
        )
      }

      const result = await backendResponse.json()
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[AI Email Compose UGG] Backend success:', {
          hasSpec: !!result.spec,
          hasWarnings: !!result.warnings,
          templateId: result.templateId,
        })
      }
      
      return NextResponse.json(result)
    } catch (error: any) {
      console.error('[AI Email Compose UGG] Backend proxy error:', {
        message: error.message,
        name: error.name,
        code: error.code,
        url: backendUrl,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      })
      
      const isConnectionError =
        error.message?.includes('fetch failed') ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT' ||
        error.message?.includes('ECONNREFUSED')
      
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
    console.error('AI Email compose-ugg error:', error)
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






