import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getSessionFromToken } from '@/lib/auth'

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Redirect /fr to / (permanent redirect)
  if (pathname === '/fr' || pathname.startsWith('/fr/')) {
    const newPath = pathname.replace(/^\/fr/, '') || '/'
    const url = request.nextUrl.clone()
    url.pathname = newPath
    return NextResponse.redirect(url, 308) // Permanent redirect
  }

  // Health check should never redirect
  if (pathname === '/health') {
    return NextResponse.next()
  }

  // Protect admin routes
  if (pathname.startsWith('/admin')) {
    // Allow access to /admin/login
    if (pathname === '/admin/login') {
      return NextResponse.next()
    }

    // Allow access to API routes (they handle their own auth)
    if (pathname.startsWith('/api/admin')) {
      return NextResponse.next()
    }

    // Check for session cookie
    const sessionToken = request.cookies.get('arq_admin_session')?.value

    if (!sessionToken) {
      // Redirect to login
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', pathname)
      return NextResponse.redirect(url)
    }

    // Verify session token
    const session = await getSessionFromToken(sessionToken)

    if (!session) {
      // Invalid or expired session, redirect to login
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      const response = NextResponse.redirect(url)
      response.cookies.delete('arq_admin_session')
      return response
    }

    // Session is valid, allow access
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
