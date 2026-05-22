'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'

export function normalizeNavPath(path: string): string {
  const trimmed = path.replace(/\/$/, '')
  return trimmed || '/'
}

type NavPendingContextValue = {
  /** Pathname effectif pour l’état actif menu (optimiste au clic). */
  effectivePath: string
  /** true pendant une navigation interne en cours. */
  isNavigating: boolean
  setPendingPath: (path: string) => void
}

const NavPendingContext = React.createContext<NavPendingContextValue | null>(null)

export function NavPendingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? ''
  const [pendingPath, setPendingPathState] = React.useState<string | null>(null)

  React.useEffect(() => {
    setPendingPathState(null)
  }, [pathname])

  const setPendingPath = React.useCallback((path: string) => {
    setPendingPathState(normalizeNavPath(path))
  }, [])

  const effectivePath = pendingPath ?? pathname
  const isNavigating = pendingPath !== null && pendingPath !== normalizeNavPath(pathname)

  const value = React.useMemo(
    () => ({ effectivePath, isNavigating, setPendingPath }),
    [effectivePath, isNavigating, setPendingPath],
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
    setPendingPath: () => {},
  }
}
