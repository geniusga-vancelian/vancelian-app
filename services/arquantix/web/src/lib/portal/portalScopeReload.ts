'use client'

import { useEffect, useState } from 'react'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'

export const PORTAL_SCOPE_CHANGED_EVENT = 'arq:portal-scope-changed'

let portalScopeRevision = 0

export function getPortalScopeRevision(): number {
  return portalScopeRevision
}

/** Invalide le cache portail et notifie les écrans (dashboard, wallets, invest…). */
export function notifyPortalScopeChanged(): void {
  portalScopeRevision += 1
  invalidatePortalCache()

  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent(PORTAL_SCOPE_CHANGED_EVENT, {
        detail: { revision: portalScopeRevision },
      }),
    )
  }
}

export function usePortalScopeRevision(): number {
  const [revision, setRevision] = useState(() => getPortalScopeRevision())

  useEffect(() => {
    const handleChange = (event: Event) => {
      const next = (event as CustomEvent<{ revision?: number }>).detail?.revision
      if (typeof next === 'number') {
        setRevision(next)
      }
    }

    window.addEventListener(PORTAL_SCOPE_CHANGED_EVENT, handleChange)
    return () => {
      window.removeEventListener(PORTAL_SCOPE_CHANGED_EVENT, handleChange)
    }
  }, [])

  return revision
}
