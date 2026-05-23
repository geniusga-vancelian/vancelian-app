import { markPortalPrivySessionReset, clearPrivyBrowserStorage } from '@/components/portal/PortalAuthPrivySessionHygiene'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export const PORTAL_LOGIN_SIGNED_OUT_PARAM = 'signed_out' as const

type PortalLoginRouter = {
  replace: (href: string, options?: { scroll?: boolean }) => void
}

/** URL login avec garde middleware pendant la purge du cookie JWT. */
export function portalLoginSignedOutHref(): string {
  return `${PORTAL_ROUTES.login}?${PORTAL_LOGIN_SIGNED_OUT_PARAM}=1`
}

/**
 * Logout navigateur : purge cookies httpOnly côté serveur puis 303 vers login.
 * Une navigation native = rechargement complet (back to login).
 */
export function portalLogoutRedirectHref(): string {
  return `/api/portal/logout?redirect=${encodeURIComponent(portalLoginSignedOutHref())}`
}

/** Purge état client avant la navigation (Privy storage, cache portail). */
export function primePortalLogoutClientState(): void {
  markPortalPrivySessionReset()
  invalidatePortalCache()
  clearPrivyBrowserStorage()
}

/** @deprecated alias — préférer `primePortalLogoutClientState`. */
export function primePortalLogoutNavigation(): void {
  primePortalLogoutClientState()
}

/** Sign-out programmatique — rechargement complet vers login. */
export function navigateToPortalLogin(router?: PortalLoginRouter): void {
  if (typeof window === 'undefined') {
    router?.replace(portalLoginSignedOutHref(), { scroll: false })
    return
  }

  primePortalLogoutClientState()
  window.location.href = portalLogoutRedirectHref()
}

/** Nettoie `?signed_out=1` sans navigation (évite un rebond middleware). */
export function stripPortalLoginSignedOutParam(): void {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  if (params.get(PORTAL_LOGIN_SIGNED_OUT_PARAM) !== '1') return
  params.delete(PORTAL_LOGIN_SIGNED_OUT_PARAM)
  const qs = params.toString()
  const next = qs ? `${PORTAL_ROUTES.login}?${qs}` : PORTAL_ROUTES.login
  window.history.replaceState(null, '', next)
}
