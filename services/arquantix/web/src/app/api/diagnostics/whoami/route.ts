import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { cookies } from 'next/headers'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function GET(request: NextRequest) {
  try {
    // EXACT SAME LOGIC AS /api/auth/probe
    const cookieStore = await cookies()
    const allCookies = cookieStore.getAll()
    const cookieNames = allCookies.map(c => c.name)
    
    const session = await getSessionFromCookie()
    const sessionFound = !!session
    const sessionEmail = session?.userEmail || null
    
    // Generate JWT (EXACT SAME METHOD as auth/probe and diagnostics)
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
        console.error('[Whoami Proxy] JWT generation error:', jwtError.message)
        jwtGenerated = false
      }
    }
    
    console.log('[Whoami Proxy] Auth check:', {
      session_found: sessionFound,
      jwt_generated: jwtGenerated,
      cookie_names: cookieNames,
    })
    
    if (!sessionFound) {
      return NextResponse.json(
        {
          error: 'not_authenticated',
          session_found: false,
          jwt_generated: false,
          cookie_names: cookieNames,
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
        },
        { status: 500 }
      )
    }

    const backendUrl = buildBackendUrl('/api/diagnostics/whoami')

    try {
      const backendResponse = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
        },
      })

      const backendStatus = backendResponse.status
      
      // Read response body ONCE - use text() first, then parse if needed
      const responseText = await backendResponse.text()
      let responseData: any = {}
      
      try {
        responseData = JSON.parse(responseText)
      } catch {
        // If not JSON, use text as error message
        responseData = { error: responseText || 'Failed to parse backend response' }
      }

      if (!backendResponse.ok) {
        console.error('[Whoami Proxy] Backend error:', {
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
      console.log('[Whoami Proxy] Backend success:', {
        session_found: sessionFound,
        jwt_generated: jwtGenerated,
        user_email: responseData.user?.email,
      })
      
      return NextResponse.json(responseData)
    } catch (error: any) {
      console.error('[Whoami Proxy] Backend proxy error:', {
        message: error.message,
        url: backendUrl,
        session_found: sessionFound,
        jwt_generated: jwtGenerated,
      })

      const isConnectionError =
        error.message?.includes('fetch failed') ||
        error.code === 'ECONNREFUSED' ||
        error.code === 'ECONNRESET' ||
        error.code === 'ETIMEDOUT'

      return NextResponse.json(
        {
          error: isConnectionError
            ? `Backend is unavailable. Please ensure the FastAPI backend is running on ${backendUrl}`
            : (error.message || 'Backend request failed'),
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
    console.error('[Whoami Proxy] Error:', error)
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) },
      { status: 500 }
    )
  }
}

