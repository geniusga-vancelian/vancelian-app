'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { usePrivy } from '@privy-io/react-auth'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  clearPrivyBrowserStorage,
  consumePortalPrivyResetFlag,
  isPortalOtpFlowActive,
  peekPortalPrivyResetFlag,
} from '@/lib/portal/portalAuthPrivySessionStorage'

export {
  abandonPortalEmailOtpFlow,
  clearPortalOtpFlow,
  clearPrivyBrowserStorage,
  markPortalOtpFlowActive,
  markPortalPrivySessionReset,
  peekPortalPrivyResetFlag,
  PORTAL_PRIVY_RESET_STORAGE_KEY,
  recoverPrivyEmailLoginSession,
} from '@/lib/portal/portalAuthPrivySessionStorage'

function isVerifyPathname(pathname: string): boolean {
  return pathname.startsWith(`${PORTAL_ROUTES.login}/verify`)
}

/**
 * Purge Privy après logout portail — uniquement sur /app/login, jamais pendant verify OTP.
 */
export function PortalAuthPrivySessionHygiene() {
  const pathname = usePathname() ?? ''
  const { ready, authenticated, logout } = usePrivy()
  const resetInFlightRef = useRef(false)

  const isVerifyPage = isVerifyPathname(pathname)
  const isLoginPage =
    pathname === PORTAL_ROUTES.login || pathname === `${PORTAL_ROUTES.login}/`

  useEffect(() => {
    if (!ready || resetInFlightRef.current || isVerifyPage || isPortalOtpFlowActive()) return

    const hasForcedReset = peekPortalPrivyResetFlag()
    if (!hasForcedReset && !authenticated) return
    if (!isLoginPage && !hasForcedReset) return

    resetInFlightRef.current = true

    void (async () => {
      const shouldAbortReset = () =>
        typeof window !== 'undefined' &&
        (isVerifyPathname(window.location.pathname) || isPortalOtpFlowActive())

      if (shouldAbortReset()) {
        resetInFlightRef.current = false
        return
      }

      try {
        if (hasForcedReset) {
          consumePortalPrivyResetFlag()
          clearPrivyBrowserStorage()
          void logout?.().catch(() => {})
          return
        }

        if (authenticated && !shouldAbortReset()) {
          clearPrivyBrowserStorage()
          void logout?.().catch(() => {})
        }
      } catch (err) {
        console.error('[portal/auth] privy session reset', err)
      } finally {
        resetInFlightRef.current = false
      }
    })()
  }, [authenticated, isLoginPage, isVerifyPage, logout, ready, pathname])

  return null
}
