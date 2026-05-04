import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { isValidLocale, type Locale } from '@/config/locales'
import { pickLocaleForRootRedirect } from '@/lib/i18n/rootLocaleRedirect'
import { LEGACY_UNPREFIXED_TOP_LEVEL } from '@/lib/i18n/legacyUnprefixedPaths'

/**
 * Hôtes connus :
 * - `console.arquantix.com` : sous-domaine privé pour l'admin/CMS uniquement.
 *   Renvoie X-Robots-Tag noindex sur toutes les réponses, redirige `/` vers
 *   `/admin/login` et 404 sur tout chemin non admin.
 * - `arquantix.com` (et autres) : site public ; les chemins `/admin*` et
 *   `/api/admin/*` sont 404 (défense en profondeur — l'ALB bloque déjà).
 *
 * Override possible via `ADMIN_CONSOLE_HOSTS` (CSV) pour dev/staging.
 */
const ADMIN_CONSOLE_HOSTS = new Set(
  (process.env.ADMIN_CONSOLE_HOSTS || 'console.arquantix.com')
    .split(',')
    .map(s => s.trim().toLowerCase())
    .filter(Boolean),
)

const NOINDEX_HEADER = 'noindex, nofollow, noarchive'

function isAdminConsoleHost(request: NextRequest): boolean {
  const host = (request.headers.get('host') || '').toLowerCase().split(':')[0]
  return ADMIN_CONSOLE_HOSTS.has(host)
}

function withConsoleHeaders(res: NextResponse, isConsole: boolean): NextResponse {
  if (isConsole) {
    res.headers.set('X-Robots-Tag', NOINDEX_HEADER)
  }
  return res
}

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
  const isConsole = isAdminConsoleHost(request)

  /**
   * `/api/admin/*` : défense en profondeur.
   * - sur les hosts publics (arquantix.com, www, ...) → 404 (l'ALB bloque déjà)
   * - sur console.arquantix.com → pass-through, X-Robots-Tag posé par middleware
   *   (le matcher inclut explicitement /api/admin/:path*)
   */
  if (pathname.startsWith('/api/admin')) {
    if (!isConsole) {
      return new NextResponse('Not Found', {
        status: 404,
        headers: { 'content-type': 'text/plain; charset=utf-8' },
      })
    }
    return withConsoleHeaders(NextResponse.next(), true)
  }

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/_vercel') ||
    pathname === '/favicon.ico'
  ) {
    return withConsoleHeaders(NextResponse.next(), isConsole)
  }

  /**
   * `console.arquantix.com` est strictement réservé à l'espace admin.
   * - `/` redirige vers `/admin/login`
   * - tout chemin hors `/admin*` répond 404
   * - `X-Robots-Tag: noindex, nofollow, noarchive` ajouté à toutes les réponses
   */
  if (isConsole) {
    if (pathname === '/' || pathname === '') {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.search = ''
      return withConsoleHeaders(NextResponse.redirect(url, 307), true)
    }
    /**
     * Exceptions servies normalement (utiles aux moteurs / navigateurs) avec
     * `X-Robots-Tag: noindex` posé en sortie :
     * - `/robots.txt` (servi par `src/app/robots.ts` host-aware → Disallow:/)
     * - `/sitemap.xml` (n'existe pas mais ne doit pas être 404 par un autre code)
     */
    const isAllowedSpecial =
      pathname === '/robots.txt' || pathname === '/sitemap.xml'
    if (!pathname.startsWith('/admin') && !isAllowedSpecial) {
      return withConsoleHeaders(
        new NextResponse('Not Found', {
          status: 404,
          headers: { 'content-type': 'text/plain; charset=utf-8' },
        }),
        true,
      )
    }
    if (isAllowedSpecial) {
      return withConsoleHeaders(NextResponse.next(), true)
    }
  }

  /**
   * Défense en profondeur : sur les hosts publics (arquantix.com, www, ...),
   * les routes `/admin*` ne sont pas servies (l'ALB renvoie déjà 404,
   * mais on protège aussi côté app si la rule disparaît).
   */
  if (!isConsole && pathname.startsWith('/admin')) {
    return new NextResponse('Not Found', {
      status: 404,
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    })
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
      return withConsoleHeaders(nextWithPathname(request), isConsole)
    }

    if (pathname.startsWith('/api/admin')) {
      return withConsoleHeaders(nextWithPathname(request), isConsole)
    }

    const sessionToken = request.cookies.get('arq_admin_session')?.value

    if (!sessionToken) {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', pathname)
      return withConsoleHeaders(NextResponse.redirect(url), isConsole)
    }

    return withConsoleHeaders(nextWithPathname(request), isConsole)
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
    '/api/admin/:path*',
  ],
}
