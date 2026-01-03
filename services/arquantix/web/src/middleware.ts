import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
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

