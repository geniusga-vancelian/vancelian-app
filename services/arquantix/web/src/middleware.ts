import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import {
  pickLocaleForRootRedirect,
  replaceLeadingLocaleInPathname,
} from '@/lib/i18n/rootLocaleRedirect'
import { LEGACY_UNPREFIXED_TOP_LEVEL } from '@/lib/i18n/legacyUnprefixedPaths'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'
import {
  ARQUANTIX_SITE_I18N_COOKIE,
  encodeSiteI18nCookie,
  parseSiteI18nCookie,
  buildSiteI18nCookieSetOptions,
  type SitePublicI18nPolicy,
} from '@/lib/i18n/siteI18nPolicyCookie'
import {
  consolePathFromPublicRequest,
  isConsoleHost,
  isConsolePathname,
  isPortalHost,
  isPortalPathname,
  isPublicPreviewPathname,
  portalPathFromPublicRequest,
  CONSOLE_PATH_PREFIX,
  PORTAL_PATH_PREFIX,
  PORTAL_ROUTES,
} from '@/lib/portal/portalRouting'
import { readPortalAccessTokenFromRequest } from '@/lib/portal/portalSession'

/** Pathname pour le layout (nav / coquille). */
function nextWithPathname(request: NextRequest) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-arq-pathname', request.nextUrl.pathname)
  return NextResponse.next({ request: { headers: requestHeaders } })
}

function nextWithPortalHeaders(request: NextRequest, pathnameOverride?: string) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-arq-pathname', pathnameOverride ?? request.nextUrl.pathname)
  requestHeaders.set('x-arq-portal', '1')
  return NextResponse.next({ request: { headers: requestHeaders } })
}

/** Locale issue du segment d’URL `/{fr|en|it}/…` (prioritaire sur le cookie en layout). */
function nextWithPathnameAndLocale(request: NextRequest, locale: Locale, policy?: SitePublicI18nPolicy) {
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-arq-pathname', request.nextUrl.pathname)
  requestHeaders.set('x-arq-locale', locale)
  const res = NextResponse.next({ request: { headers: requestHeaders } })
  if (policy) {
    applyPublicI18nCookies(res, policy)
  }
  return res
}

async function fetchSitePublicI18nPolicy(request: NextRequest): Promise<SitePublicI18nPolicy> {
  const cached = parseSiteI18nCookie(request.cookies.get(ARQUANTIX_SITE_I18N_COOKIE)?.value)
  if (cached) return cached

  try {
    const url = new URL('/api/site/i18n-policy', request.nextUrl.origin)
    const res = await fetch(url, { next: { revalidate: 30 } })
    if (res.ok) {
      const j = (await res.json()) as { multilingual?: boolean; defaultLocale?: string }
      const multilingual = j.multilingual !== false
      const d =
        j.defaultLocale && isValidLocale(j.defaultLocale) ? j.defaultLocale : (defaultLocale as Locale)
      return { multilingual, defaultLocale: d }
    }
  } catch {
    /* repli cookie / défaut */
  }
  const parsed = parseSiteI18nCookie(request.cookies.get(ARQUANTIX_SITE_I18N_COOKIE)?.value)
  if (parsed) return parsed
  return { multilingual: true, defaultLocale: defaultLocale as Locale }
}

function applyPublicI18nCookies(res: NextResponse, p: SitePublicI18nPolicy) {
  const o = buildSiteI18nCookieSetOptions()
  res.cookies.set(ARQUANTIX_SITE_I18N_COOKIE, encodeSiteI18nCookie(p), o)
  if (!p.multilingual) {
    res.cookies.set(ARQUANTIX_LOCALE_COOKIE, '', { path: '/', maxAge: 0, sameSite: 'lax' })
  }
}

/**
 * Phase 2B — SEO i18n :
 * - `/` → locale selon politique (site monolingue = défaut admin, sans cookie préférence)
 * - Préfixe `/{fr|en|it}/…` : si monolingue, redirection vers la locale par défaut
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/_vercel') ||
    pathname.startsWith('/fonts/') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next()
  }

  if (pathname === '/health') {
    return nextWithPathname(request)
  }

  const host = request.headers.get('host')
  const consoleHost = isConsoleHost(host)

  if (consoleHost) {
    if (isPublicPreviewPathname(pathname)) {
      return nextWithPathname(request)
    }

    if (/^\/(fr|en|it)(?:\/|$)/.test(pathname)) {
      const url = request.nextUrl.clone()
      url.pathname = `${CONSOLE_PATH_PREFIX}/pages`
      return NextResponse.redirect(url)
    }

    const consolePath = consolePathFromPublicRequest(pathname, true)
    if (consolePath !== pathname) {
      const url = request.nextUrl.clone()
      url.pathname = consolePath
      const requestHeaders = new Headers(request.headers)
      requestHeaders.set('x-arq-pathname', consolePath)
      requestHeaders.set('x-arq-console', '1')
      return NextResponse.rewrite(url, {
        request: { headers: requestHeaders },
      })
    }

    const effectivePath = isConsolePathname(pathname) ? pathname : consolePath
    if (
      effectivePath === CONSOLE_PATH_PREFIX ||
      effectivePath === `${CONSOLE_PATH_PREFIX}/`
    ) {
      const url = request.nextUrl.clone()
      url.pathname = `${CONSOLE_PATH_PREFIX}/pages`
      return NextResponse.redirect(url)
    }

    if (
      effectivePath.startsWith(CONSOLE_PATH_PREFIX) &&
      effectivePath !== '/admin/login' &&
      effectivePath !== '/admin/login0' &&
      effectivePath !== '/admin/signup' &&
      !request.cookies.get('arq_admin_session')?.value
    ) {
      const url = request.nextUrl.clone()
      url.pathname = '/admin/login'
      url.searchParams.set('redirect', effectivePath)
      return NextResponse.redirect(url)
    }

    return nextWithPathname(request)
  }

  const appHost = isPortalHost(host)
  const portalPath = appHost ? portalPathFromPublicRequest(pathname, true) : pathname
  const onPortalSurface = appHost || isPortalPathname(pathname)

  if (onPortalSurface) {
    if (isPublicPreviewPathname(pathname)) {
      return nextWithPathname(request)
    }

    if (appHost && portalPath !== pathname) {
      const url = request.nextUrl.clone()
      url.pathname = portalPath
      const requestHeaders = new Headers(request.headers)
      requestHeaders.set('x-arq-pathname', portalPath)
      requestHeaders.set('x-arq-portal', '1')
      return NextResponse.rewrite(url, {
        request: { headers: requestHeaders },
      })
    }

    const effectivePath = isPortalPathname(pathname) ? pathname : portalPath
    const portalSession = readPortalAccessTokenFromRequest(request)
    const isLoginSurface =
      effectivePath === PORTAL_ROUTES.login ||
      effectivePath.startsWith(`${PORTAL_ROUTES.login}/`)
    const isDashboard = effectivePath.startsWith(PORTAL_ROUTES.dashboard)

    if (effectivePath === PORTAL_PATH_PREFIX || effectivePath === `${PORTAL_PATH_PREFIX}/`) {
      const url = request.nextUrl.clone()
      url.pathname = portalSession ? PORTAL_ROUTES.dashboard : PORTAL_ROUTES.login
      return NextResponse.redirect(url)
    }

    if (isDashboard && !portalSession) {
      const url = request.nextUrl.clone()
      url.pathname = PORTAL_ROUTES.login
      url.searchParams.set('redirect', effectivePath)
      return NextResponse.redirect(url)
    }

    if (isLoginSurface && portalSession) {
      const signingOut = request.nextUrl.searchParams.get('signed_out') === '1'
      if (!signingOut) {
        const url = request.nextUrl.clone()
        url.pathname = PORTAL_ROUTES.dashboard
        return NextResponse.redirect(url)
      }
    }

    return nextWithPortalHeaders(request)
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

  let lazyPolicy: SitePublicI18nPolicy | null = null
  const getPolicy = async () => {
    if (!lazyPolicy) {
      lazyPolicy = await fetchSitePublicI18nPolicy(request)
    }
    return lazyPolicy
  }

  if (pathname === '/' || pathname === '') {
    const p = await getPolicy()
    const locale = pickLocaleForRootRedirect(request, p)
    const url = request.nextUrl.clone()
    url.pathname = `/${locale}`
    url.searchParams.delete('locale')
    const res = NextResponse.redirect(url, 307)
    applyPublicI18nCookies(res, p)
    return res
  }

  const singleSeg = pathname.match(/^\/([^/]+)\/?$/)
  if (singleSeg) {
    const seg = singleSeg[1]
    if (!isValidLocale(seg) && !LEGACY_UNPREFIXED_TOP_LEVEL.has(seg) && !seg.includes('.')) {
      const p = await getPolicy()
      const url = request.nextUrl.clone()
      url.pathname = `/${p.defaultLocale}/${seg}`
      const res = NextResponse.redirect(url, 308)
      applyPublicI18nCookies(res, p)
      return res
    }
  }

  const localePrefix = pathname.match(/^\/(fr|en|it)(?:\/|$)/)
  if (localePrefix?.[1] && isValidLocale(localePrefix[1])) {
    const loc = localePrefix[1] as Locale
    const p = await getPolicy()
    if (!p.multilingual && loc !== p.defaultLocale) {
      const url = request.nextUrl.clone()
      url.pathname = replaceLeadingLocaleInPathname(pathname, p.defaultLocale)
      const res = NextResponse.redirect(url, 308)
      applyPublicI18nCookies(res, p)
      return res
    }
    return nextWithPathnameAndLocale(request, loc, p)
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
  matcher: ['/((?!api|_next/static|_next/image|favicon\\.ico).*)'],
}
