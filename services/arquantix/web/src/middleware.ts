import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getSessionFromToken } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

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

  // Admin routes protection
  if (pathname.startsWith('/admin')) {
    if (pathname === '/admin/login') {
      // Allow access to login page
      return NextResponse.next()
    }

    // Get session token from cookie
    const token = request.cookies.get('arq_admin_session')?.value

    if (!token) {
      // Redirect to login if not authenticated
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      return NextResponse.redirect(url)
    }

    // Verify session token
    try {
      const session = await getSessionFromToken(token)
      
      if (!session) {
        // Invalid or expired session
        const url = request.nextUrl.clone()
        url.pathname = '/admin/login'
        const response = NextResponse.redirect(url)
        response.cookies.delete('arq_admin_session')
        return response
      }

      // Session is valid, allow access
      return NextResponse.next()
    } catch (error) {
      // Error verifying session, redirect to login
      console.error('Middleware session verification error:', error)
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      const response = NextResponse.redirect(url)
      response.cookies.delete('arq_admin_session')
      return response
    }
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
