import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { cookies } from 'next/headers'
import { signAdminBackendJwtFromSession } from '@/lib/backend-jwt'

export async function GET(request: NextRequest) {
  try {
    // Read cookies from Next.js cookies() helper
    const cookieStore = await cookies()
    const allCookies = cookieStore.getAll()
    const cookieNames = allCookies.map(c => c.name)
    
    // Also check raw cookie header from request
    const cookieHeader = request.headers.get('cookie')
    const hasCookieHeader = !!cookieHeader
    
    // Extract cookie names from raw header (if present)
    const rawCookieNames: string[] = []
    if (cookieHeader) {
      cookieHeader.split(';').forEach(cookie => {
        const name = cookie.split('=')[0]?.trim()
        if (name) {
          rawCookieNames.push(name)
        }
      })
    }
    
    // Try to get session using the same helper as other proxies
    const session = await getSessionFromCookie()
    const sessionFound = !!session
    const sessionEmail = session?.userEmail || null
    
    // Try to generate JWT if session found (same method as other proxies)
    let jwtGenerated = false
    if (sessionFound && session) {
      try {
        const signed = await signAdminBackendJwtFromSession(session)
        jwtGenerated = signed.ok && !!signed.token
      } catch (jwtError: any) {
        console.error('[Auth Probe] JWT generation error:', jwtError.message)
        jwtGenerated = false
      }
    }
    
    return NextResponse.json({
      cookie_names: cookieNames,
      raw_cookie_names: rawCookieNames,
      has_cookie_header: hasCookieHeader,
      session_found: sessionFound,
      session_email: sessionEmail,
      jwt_generated: jwtGenerated,
    })
  } catch (error) {
    console.error('[Auth Probe] Error:', error)
    const errorMsg = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json(
      {
        error: typeof errorMsg === 'string' ? errorMsg : String(errorMsg),
        cookie_names: [],
        has_cookie_header: false,
        session_found: false,
        session_email: null,
        jwt_generated: false,
      },
      { status: 500 }
    )
  }
}






