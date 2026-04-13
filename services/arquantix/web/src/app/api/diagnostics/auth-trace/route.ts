import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import { cookies } from 'next/headers'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function POST(request: NextRequest) {
  try {
    // EXACT SAME LOGIC AS /api/auth/probe
    const cookieStore = await cookies()
    const allCookies = cookieStore.getAll()
    const cookieNames = allCookies.map(c => c.name)
    
    const session = await getSessionFromCookie()
    const sessionFound = !!session
    const sessionEmail = session?.userEmail || null
    
    // Generate JWT (EXACT SAME METHOD as other proxies)
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
        console.error('[Auth Trace Proxy] JWT generation error:', jwtError.message)
        jwtGenerated = false
      }
    }
    
    console.log('[Auth Trace Proxy] Auth check:', {
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

    const backendUrl = buildBackendUrl('/api/diagnostics/auth-trace')

    try {
      const backendResponse = await fetch(backendUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
        },
      })

      const backendStatus = backendResponse.status
      const backendBodyText = await backendResponse.text()
      let backendBody: any = {}
      try {
        backendBody = JSON.parse(backendBodyText)
      } catch {
        backendBody = { raw: backendBodyText.substring(0, 500) }
      }

      // Return trace info even if status is not 200 (because it's a debug endpoint)
      return NextResponse.json({
        ...backendBody,
        proxy_info: {
          session_found: sessionFound,
          jwt_generated: jwtGenerated,
          cookie_names: cookieNames,
          backend_status: backendStatus,
        },
      })
    } catch (error: any) {
      console.error('[Auth Trace Proxy] Backend proxy error:', {
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
    console.error('[Auth Trace Proxy] Error:', error)
    const errorMsg = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json(
      { error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg) },
      { status: 500 }
    )
  }
}






