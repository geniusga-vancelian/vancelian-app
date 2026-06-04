'use client'

import * as React from 'react'
import { flushSync } from 'react-dom'
import { usePathname } from 'next/navigation'
import {
  resolveEffectiveNavPath,
  resolveNavIsNavigating,
  resolveNavPendingBarVisible,
  shouldBeginPortalNavigation,
} from '@/lib/portal/portalNavInstantFeedback'

export function normalizeNavPath(path: string): string {
  const trimmed = path.replace(/\/$/, '')
  return trimmed || '/'
}

type NavPendingContextValue = {
  /** Pathname effectif pour l’état actif menu (optimiste au clic). */
  effectivePath: string
  /** true pendant une navigation interne en cours. */
  isNavigating: boolean
  /** Barre terracotta : dès destination optimiste ≠ pathname réel (G4-B1.5). */
  showPendingBar: boolean
  /** Démarre la navigation optimiste (pointerdown, rendu synchrone). */
  beginNavigation: (path: string) => void
  /** @deprecated Préférer beginNavigation */
  setPendingPath: (path: string) => void
}

const NavPendingContext = React.createContext<NavPendingContextValue | null>(null)

export function NavPendingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? ''
  const [pendingPath, setPendingPathState] = React.useState<string | null>(null)

  React.useEffect(() => {
    setPendingPathState(null)
  }, [pathname])

  const beginNavigation = React.useCallback(
    (path: string) => {
      const normalized = normalizeNavPath(path)
      if (!shouldBeginPortalNavigation(pathname, normalized)) return
      if (pendingPath === normalized) return
      flushSync(() => {
        setPendingPathState(normalized)
      })
    },
    [pathname, pendingPath],
  )

  const setPendingPath = beginNavigation

  const effectivePath = resolveEffectiveNavPath(pendingPath, pathname)
  const isNavigating = resolveNavIsNavigating(pendingPath, pathname)
  const showPendingBar = resolveNavPendingBarVisible(pendingPath, pathname)

  const value = React.useMemo(
    () => ({ effectivePath, isNavigating, showPendingBar, beginNavigation, setPendingPath }),
    [effectivePath, isNavigating, showPendingBar, beginNavigation, setPendingPath],
  )

  return <NavPendingContext.Provider value={value}>{children}</NavPendingContext.Provider>
}

export function useNavPending(): NavPendingContextValue {
  const ctx = React.useContext(NavPendingContext)
  const pathname = usePathname() ?? ''

  if (ctx) return ctx

  return {
    effectivePath: pathname,
    isNavigating: false,
    showPendingBar: false,
    beginNavigation: () => {},
    setPendingPath: () => {},
  }
}
