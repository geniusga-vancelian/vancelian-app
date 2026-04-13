import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { buildBackendUrl } from '@/lib/backend'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const composeEmailSchema = z.object({
  prompt: z.string().min(1).max(2000),
  locale: z.string().regex(/^[a-z]{2}$/).optional().default('en'),
  previous_spec: z.any().optional(), // EmailSpec, validated later
  templateId: z.string().optional(),
  templateSource: z.enum(['hardcoded', 'db']).optional().default('hardcoded'),
  lockStructure: z.boolean().optional().default(true),
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { prompt, locale, previous_spec, templateId, templateSource, lockStructure } = composeEmailSchema.parse(body)

    // Proxy to FastAPI backend (which handles templates and locking)
    const backendUrl = buildBackendUrl('/api/ai/email/compose')
    
    if (process.env.NODE_ENV === 'development') {
      console.log('[AI Email Compose] Backend URL:', backendUrl)
      console.log('[AI Email Compose] Request body:', {
        prompt: prompt.substring(0, 100) + '...',
        locale,
        templateId,
        templateSource,
        lockStructure,
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
          templateId: templateId || undefined,
          templateSource: templateSource || 'hardcoded',
          lockStructure: lockStructure ?? true,
        }),
      })

      if (process.env.NODE_ENV === 'development') {
        console.log('[AI Email Compose] Backend response status:', backendResponse.status, backendResponse.statusText)
      }

      if (!backendResponse.ok) {
        const errorText = await backendResponse.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { error: errorText || 'Backend error' }
        }
        console.error('[AI Email Compose] Backend error response:', {
          status: backendResponse.status,
          statusText: backendResponse.statusText,
          url: backendUrl,
          error: errorData
        })
        
        // Return backend error directly (don't fallback)
        const errorMsg = errorData.detail || errorData.error || errorData.message || `Backend request failed (${backendResponse.status})`
        // Ensure error is a string
        const errorMessage = typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)
        
        console.error('[AI Email Compose] Returning error to frontend:', {
          status: backendResponse.status,
          errorMessage,
          errorData,
        })
        
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
        console.log('[AI Email Compose] Backend success:', {
          hasSpec: !!result.spec,
          hasWarnings: !!result.warnings,
          templateId: result.templateId,
        })
      }
      
      return NextResponse.json(result)
    } catch (error: any) {
      console.error('[AI Email Compose] Backend proxy error:', {
        message: error.message,
        name: error.name,
        code: error.code,
        url: backendUrl,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      })
      
      // Check if backend is unreachable (connection error)
      const isConnectionError =
        error.message?.includes('fetch failed') ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT' ||
        error.message?.includes('ECONNREFUSED')
      
      // Only use fallback if explicitly enabled
      const allowFallback = process.env.EMAIL_BUILDER_ALLOW_FALLBACK === 'true'
      
      if (isConnectionError && allowFallback) {
        console.warn('[AI Email Compose] Backend unreachable, using local fallback (EMAIL_BUILDER_ALLOW_FALLBACK=true)')
        
        // Fallback: use local composeEmailSpec (without templates/locking)
        try {
          const { composeEmailSpec } = await import('@/lib/ai-email/composeEmail')
          const { buildMjml } = await import('@/lib/ai-email/buildMjml')
          const { compileMjml } = await import('@/lib/ai-email/compileMjml')
          
          const { spec, assistantText } = await composeEmailSpec(
            prompt,
            previous_spec || null,
            locale || 'en'
          )
          
          // Build MJML and HTML
          const mjml = buildMjml(spec)
          const { html, error: compileError } = await compileMjml(mjml)
          
          const warnings: string[] = [
            'Backend unavailable, using local fallback (templates and structure locking disabled)'
          ]
          if (compileError) {
            warnings.push(`MJML compilation warning: ${compileError}`)
            console.warn('[AI Email Compose] MJML compilation error:', compileError)
          }
          
          return NextResponse.json({
            assistant_text: assistantText,
            spec,
            mjml,
            html,
            warnings,
            templateId: templateId || undefined,
            locked: false,
          })
        } catch (fallbackError: any) {
          console.error('[AI Email Compose] Fallback compose error:', {
            message: fallbackError.message,
            name: fallbackError.name,
          })
          
          const detailsMsg = fallbackError.message || 'Unknown error'
          return NextResponse.json(
            {
              error: 'Backend unavailable and fallback failed. Please ensure the FastAPI backend is running.',
              code: 'BACKEND_UNAVAILABLE',
              details: typeof detailsMsg === 'string' ? detailsMsg : String(detailsMsg)
            },
            { status: 502 }
          )
        }
      }
      
      // Backend error but no fallback allowed, or non-connection error
      const errorMsg = isConnectionError
        ? `Backend is unavailable. Please ensure the FastAPI backend is running on ${backendUrl}`
        : (error.message || 'Backend request failed')
      
      console.error('[AI Email Compose] Connection/backend error:', {
        isConnectionError,
        errorMessage: errorMsg,
        url: backendUrl,
        originalError: error.message,
      })
      
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
    console.error('AI Email compose error:', error)
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
