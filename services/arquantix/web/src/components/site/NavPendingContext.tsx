'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'

export function normalizeNavPath(path: string): string {
  const trimmed = path.replace(/\/$/, '')
  return trimmed || '/'
}

type NavPendingContextValue = {
  /** Pathname réel — seule source de vérité pour menu actif (URL-first). */
  effectivePath: string
  /** Conservé pour compat site ; toujours false (plus de pending optimiste au clic). */
  isNavigating: boolean
  /** No-op — la navigation passe par Next Link natif. */
  setPendingPath: (path: string) => void
}

const NavPendingContext = React.createContext<NavPendingContextValue | null>(null)

export function NavPendingProvider({ children }: { children: React.ReactNode }) {
  const pathname = normalizeNavPath(usePathname() ?? '')

  const value = React.useMemo(
    () => ({
      effectivePath: pathname,
      isNavigating: false,
      setPendingPath: () => {},
    }),
    [pathname],
  )

  return <NavPendingContext.Provider value={value}>{children}</NavPendingContext.Provider>
}

export function useNavPending(): NavPendingContextValue {
  const pathname = normalizeNavPath(usePathname() ?? '')
  const ctx = React.useContext(NavPendingContext)

  if (ctx) return ctx

  return {
    effectivePath: pathname,
    isNavigating: false,
    setPendingPath: () => {},
  }
}
