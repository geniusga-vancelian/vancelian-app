import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { isValidLocale, type Locale } from '@/config/locales'
import { pickLocaleForRootRedirect } from '@/lib/i18n/rootLocaleRedirect'
import { LEGACY_UNPREFIXED_TOP_LEVEL } from '@/lib/i18n/legacyUnprefixedPaths'

/** Pathname pour le layout (nav / coquille). */
function nextWithPathname(request: NextRequest) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-arq-pathname', request.nextUrl.pathname)
  return NextResponse.next({ request: { headers: requestHeaders } })
}

/** Locale issue du segment d’URL `/{fr|en|it}/…` (prioritaire sur le cookie en layout). */
function nextWithPathnameAndLocale(request: NextRequest, locale: Locale) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-arq-pathname', request.nextUrl.pathname)
  requestHeaders.set('x-arq-locale', locale)
  return NextResponse.next({ request: { headers: requestHeaders } })
}

/**
 * Phase 2B — SEO i18n :
 * - `/` → `/{locale}` (query > cookie > Accept-Language > défaut)
 * - `/{fr|en|it}` et `/{fr|en|it}/…` : header `x-arq-locale`
 * - ancienne URL CMS `/slug` (un segment) → `/fr/slug` (308), sauf routes legacy listées
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/_vercel') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next()
  }

  if (pathname === '/health') {
    return nextWithPathname(request)
  }

  if (pathname === '/guide' || pathname.startsWith('/guide/')) {
    const sessionToken = request.cookies.get('arq_admin_session')?.value
    if (!sessionToken) {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', pathname)
      return NextResponse.redirect(url)
    }
    return nextWithPathname(request)
  }

  if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
    const url = request.nextUrl.clone()
    url.pathname = pathname.replace('/dashboard', '/admin') || '/admin'
    return NextResponse.redirect(url, 307)
  }

  /**
   * L’admin vit uniquement sous `app/admin` (pas sous `app/[locale]/admin`).
   * Une URL du type `/fr/admin/pages/article` ne matche aucune page → 404 silencieux.
   * On normalise vers `/admin/…` (même cookie, même session).
   */
  const adminAfterLocale = pathname.match(/^\/(fr|en|it)(\/admin(?:\/|$).*)$/)
  if (adminAfterLocale) {
    const url = request.nextUrl.clone()
    url.pathname = adminAfterLocale[2]
    return NextResponse.redirect(url, 308)
  }

  if (pathname.startsWith('/admin')) {
    if (
      pathname === '/admin/login' ||
      pathname === '/admin/login0' ||
      pathname === '/admin/signup'
    ) {
      return nextWithPathname(request)
    }

    if (pathname.startsWith('/api/admin')) {
      return nextWithPathname(request)
    }

    const sessionToken = request.cookies.get('arq_admin_session')?.value

    if (!sessionToken) {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', pathname)
      return NextResponse.redirect(url)
    }

    return nextWithPathname(request)
  }

  if (pathname === '/' || pathname === '') {
    const locale = pickLocaleForRootRedirect(request)
    const url = request.nextUrl.clone()
    url.pathname = `/${locale}`
    url.searchParams.delete('locale')
    return NextResponse.redirect(url, 307)
  }

  // URLs CMS historiques sans préfixe : /slug → /fr/slug (locale par défaut du site)
  const singleSeg = pathname.match(/^\/([^/]+)\/?$/)
  if (singleSeg) {
    const seg = singleSeg[1]
    if (!isValidLocale(seg) && !LEGACY_UNPREFIXED_TOP_LEVEL.has(seg) && !seg.includes('.')) {
      const url = request.nextUrl.clone()
      url.pathname = `/fr/${seg}`
      return NextResponse.redirect(url, 308)
    }
  }

  // `/{fr|en|it}` ou `/{fr|en|it}/…` — délimite la locale (évite `/france` interprété comme `fr`).
  const localePrefix = pathname.match(/^\/(fr|en|it)(?:\/|$)/)
  if (localePrefix?.[1] && isValidLocale(localePrefix[1])) {
    return nextWithPathnameAndLocale(request, localePrefix[1] as Locale)
  }

  const helpLegacyThree = pathname.match(/^\/help\/([^/]+)\/([^/]+)\/([^/]+)\/?$/)
  if (helpLegacyThree) {
    const url = request.nextUrl.clone()
    url.pathname = `/help/${helpLegacyThree[1]}/${helpLegacyThree[3]}`
    return NextResponse.redirect(url, 308)
  }

  const helpLegacyThreeLocale = pathname.match(/^\/(fr|en|it)\/help\/([^/]+)\/([^/]+)\/([^/]+)\/?$/)
  if (helpLegacyThreeLocale) {
    const url = request.nextUrl.clone()
    url.pathname = `/${helpLegacyThreeLocale[1]}/help/${helpLegacyThreeLocale[2]}/${helpLegacyThreeLocale[4]}`
    return NextResponse.redirect(url, 308)
  }

  const academyLegacyThree = pathname.match(/^\/academy\/([^/]+)\/([^/]+)\/([^/]+)\/?$/)
  if (academyLegacyThree) {
    const url = request.nextUrl.clone()
    url.pathname = `/academy/${academyLegacyThree[1]}/${academyLegacyThree[3]}`
    return NextResponse.redirect(url, 308)
  }

  const academyLegacyThreeLocale = pathname.match(
    /^\/(fr|en|it)\/academy\/([^/]+)\/([^/]+)\/([^/]+)\/?$/,
  )
  if (academyLegacyThreeLocale) {
    const url = request.nextUrl.clone()
    url.pathname = `/${academyLegacyThreeLocale[1]}/academy/${academyLegacyThreeLocale[2]}/${academyLegacyThreeLocale[4]}`
    return NextResponse.redirect(url, 308)
  }

  return nextWithPathname(request)
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon\\.ico).*)',
  ],
}
