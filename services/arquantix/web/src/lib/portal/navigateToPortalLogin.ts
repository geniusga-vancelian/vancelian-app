import { markPortalPrivySessionReset } from '@/components/portal/PortalAuthPrivySessionHygiene'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { preloadPrivyPortalProvider } from '@/lib/portal/preloadPrivyPortalProvider'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export const PORTAL_LOGIN_SIGNED_OUT_PARAM = 'signed_out' as const

type PortalLoginRouter = {
  replace: (href: string, options?: { scroll?: boolean }) => void
}

function portalLoginHref(signedOut: boolean): string {
  if (!signedOut) return PORTAL_ROUTES.login
  return `${PORTAL_ROUTES.login}?${PORTAL_LOGIN_SIGNED_OUT_PARAM}=1`
}

/**
 * Déconnexion perçue instantanée :
 * navigation immédiate vers login (skeleton Suspense) + purge session API en arrière-plan.
 * `signed_out=1` évite le rebond middleware login → dashboard tant que le cookie JWT existe.
 */
export function navigateToPortalLogin(router: PortalLoginRouter): void {
  markPortalPrivySessionReset()
  invalidatePortalCache()
  preloadPrivyPortalProvider()
  router.replace(portalLoginHref(true), { scroll: false })

  void fetch('/api/portal/logout', {
    method: 'POST',
    credentials: 'include',
    keepalive: true,
  })
    .then(() => {
      router.replace(PORTAL_ROUTES.login, { scroll: false })
    })
    .catch((err) => {
      console.error('[portal/logout]', err)
    })
}
