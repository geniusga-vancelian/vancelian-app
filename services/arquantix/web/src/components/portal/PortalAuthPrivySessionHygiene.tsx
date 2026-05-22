'use client'

import { useEffect, useRef } from 'react'
import { usePathname } from 'next/navigation'
import { usePrivy } from '@privy-io/react-auth'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export const PORTAL_PRIVY_RESET_STORAGE_KEY = 'arq_portal_privy_reset'
const PORTAL_OTP_FLOW_STORAGE_KEY = 'arq_portal_otp_flow'

/** Signal logout portail → purge session Privy au prochain montage login. */
export function markPortalPrivySessionReset(): void {
  clearPortalOtpFlow()
  try {
    sessionStorage.setItem(PORTAL_PRIVY_RESET_STORAGE_KEY, '1')
  } catch {
    /* ignore */
  }
}

/** Empêche la purge Privy pendant un flux OTP actif (login → verify / resend). */
export function markPortalOtpFlowActive(): void {
  try {
    sessionStorage.setItem(PORTAL_OTP_FLOW_STORAGE_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function clearPortalOtpFlow(): void {
  try {
    sessionStorage.removeItem(PORTAL_OTP_FLOW_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

/** Abandon verify/resend — permet au login de repartir sur un flux OTP propre. */
export function abandonPortalEmailOtpFlow(): void {
  clearPortalOtpFlow()
}

function isPortalOtpFlowActive(): boolean {
  try {
    return sessionStorage.getItem(PORTAL_OTP_FLOW_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function peekPortalPrivyResetFlag(): boolean {
  try {
    return sessionStorage.getItem(PORTAL_PRIVY_RESET_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function consumePortalPrivyResetFlag(): boolean {
  try {
    if (sessionStorage.getItem(PORTAL_PRIVY_RESET_STORAGE_KEY) !== '1') return false
    sessionStorage.removeItem(PORTAL_PRIVY_RESET_STORAGE_KEY)
    return true
  } catch {
    return false
  }
}

function isVerifyPathname(pathname: string): boolean {
  return pathname.startsWith(`${PORTAL_ROUTES.login}/verify`)
}

/** Purge synchrone des tokens Privy persistés (sans appeler logout() async). */
function clearPrivyBrowserStorage(): void {
  if (typeof window === 'undefined') return
  try {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith('privy:') || key.startsWith('privy-')) {
        localStorage.removeItem(key)
      }
    }
  } catch {
    /* ignore */
  }
}

/**
 * Réinitialise l’état email OTP Privy après « Unauthorized » (resend / sendCode).
 * Purge d’abord le storage local, puis logout SDK si besoin — évite les courses
 * async qui cassent le sendCode suivant sans hard refresh.
 */
export async function recoverPrivyEmailLoginSession(
  logout?: () => Promise<void>,
): Promise<void> {
  clearPrivyBrowserStorage()
  if (logout) {
    try {
      await logout()
    } catch {
      /* session déjà invalide */
    }
  }
  clearPrivyBrowserStorage()
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
          await recoverPrivyEmailLoginSession(logout)
          return
        }

        if (authenticated && !shouldAbortReset()) {
          await recoverPrivyEmailLoginSession(logout)
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
