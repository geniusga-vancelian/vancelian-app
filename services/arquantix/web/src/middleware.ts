import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

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

  // Redirect /dashboard to /admin
  if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
    const url = request.nextUrl.clone()
    url.pathname = pathname.replace('/dashboard', '/admin') || '/admin'
    return NextResponse.redirect(url, 307) // Temporary redirect
  }

  // Admin routes protection
  // Note: Full authentication check is done in API routes and page components
  // Middleware only checks for the presence of the session cookie
  if (pathname.startsWith('/admin')) {
    // Entrée publique admin (sans session)
    if (
      pathname === '/admin/login' ||
      pathname === '/admin/login0' ||
      pathname === '/admin/signup'
    ) {
      return NextResponse.next()
    }

    // Allow access to API routes (they handle their own auth)
    if (pathname.startsWith('/api/admin')) {
      return NextResponse.next()
    }

    // Check for session cookie
    const sessionToken = request.cookies.get('arq_admin_session')?.value

    if (!sessionToken) {
      // Redirect to login if no session cookie
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', pathname)
      return NextResponse.redirect(url)
    }

    // Session cookie exists, let the page/API handle validation
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Exclure tout le préfixe `/_next` (pas seulement static/image) : en dev, webpack-hmr,
     * flight, chunks, etc. ne doivent jamais passer par ce middleware (risque de 404/500 ou
     * comportements étranges si la logique évolue).
     */
    '/((?!api|_next|favicon\\.ico).*)',
  ],
}
