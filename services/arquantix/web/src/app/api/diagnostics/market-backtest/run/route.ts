import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { z } from 'zod'
import { cookies } from 'next/headers'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

const diagnosticRequestSchema = z.object({
  mode: z.enum(['quick', 'full']).default('quick'),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
})

export async function POST(request: NextRequest) {
  try {
    // EXACT SAME LOGIC AS /api/auth/probe
    // Read cookies from Next.js cookies() helper
    const cookieStore = await cookies()
    const allCookies = cookieStore.getAll()
    const cookieNames = allCookies.map(c => c.name)
    
    // Try to get session using the same helper as auth/probe
    const session = await getSessionFromCookie()
    const sessionFound = !!session
    const sessionEmail = session?.userEmail || null
    
    // Try to generate JWT if session found (EXACT SAME METHOD as auth/probe)
    let jwtGenerated = false
    let jwtToken: string | null = null
    if (sessionFound && session) {
      try {
        const signed = await signAdminBackendJwtFromSession(session)
        if (signed.ok) {
          jwtToken = signed.token
          jwtGenerated = true
        } else {
          jwtGenerated = false
        }
      } catch (jwtError: any) {
        console.error('[Diagnostics Proxy] JWT generation error:', jwtError.message)
        jwtGenerated = false
      }
    }
    
    // Debug log (server-side)
    console.log('[Diagnostics Proxy] Auth check:', {
      session_found: sessionFound,
      jwt_generated: jwtGenerated,
      cookie_names: cookieNames,
      backend_url: buildBackendUrl('/api/diagnostics/market-backtest/run'),
    })
    
    if (!sessionFound) {
      return NextResponse.json(
        {
          error: 'not_authenticated',
          session_found: false,
          jwt_generated: false,
          cookie_names: cookieNames,
          hint: 'login required',
        },
        { status: 401 }
      )
    }
    
    if (!jwtGenerated || !jwtToken) {
      return NextResponse.json(
        {
          error: 'jwt_generation_failed',
          session_found: true,
          jwt_generated: false,
          cookie_names: cookieNames,
          hint: 'JWT generation failed despite session found',
        },
        { status: 500 }
      )
    }

    const body = await request.json()
    const validated = diagnosticRequestSchema.parse(body)

    const backendUrl = buildBackendUrl('/api/diagnostics/market-backtest/run')

    // Debug log before calling backend
    console.log('[Diagnostics Proxy] Calling backend:', {
      session_found: sessionFound,
      jwt_generated: jwtGenerated,
      backend_url: backendUrl,
      mode: validated.mode,
    })

    try {
      const backendResponse = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`,
        },
        body: JSON.stringify(validated),
      })

      const backendStatus = backendResponse.status
      
      // Read response body ONCE - use text() first, then parse if needed
      const responseText = await backendResponse.text()
      let responseData: any = {}
      
      try {
        responseData = JSON.parse(responseText)
      } catch {
        // If not JSON, use text as error message
        responseData = { error: responseText || 'Backend error' }
      }

      if (!backendResponse.ok) {
        console.error('[Diagnostics Proxy] Backend error:', {
          status: backendStatus,
          body: responseData,
          session_found: sessionFound,
          jwt_generated: jwtGenerated,
        })

        const errorMsg = responseData.detail || responseData.error || responseData.message || `Backend request failed (${backendStatus})`
        return NextResponse.json(
          {
            error: typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg),
            code: 'BACKEND_ERROR',
            status: backendStatus,
            session_found: sessionFound,
            jwt_generated: jwtGenerated,
            cookie_names: cookieNames,
            backend_status: backendStatus,
            backend_body: typeof responseText === 'string' ? responseText.substring(0, 500) : String(responseText).substring(0, 500),
          },
          { status: backendStatus }
        )
      }

      // Success: return parsed JSON
      console.log('[Diagnostics Proxy] Backend success:', {
        session_found: sessionFound,
        jwt_generated: jwtGenerated,
        has_report: !!responseData.report,
      })
      
      return NextResponse.json(responseData)
    } catch (error: any) {
      console.error('[Diagnostics Proxy] Backend proxy error:', {
        message: error.message,
        name: error.name,
        code: error.code,
        url: backendUrl,
        session_found: sessionFound,
        jwt_generated: jwtGenerated,
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
          session_found: sessionFound,
          jwt_generated: jwtGenerated,
          cookie_names: cookieNames,
        },
        { status: 502 }
      )
    }
  } catch (error) {
    console.error('[Diagnostics Proxy] Error:', error)
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

