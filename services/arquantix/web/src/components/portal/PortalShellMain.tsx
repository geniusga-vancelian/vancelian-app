'use client'

import type { ReactNode } from 'react'
import { PortalRouteCachedPreview } from '@/components/portal/PortalRouteCachedPreview'
import { resolvePortalShellMainNavMode } from '@/components/portal/portalShellMainNavigation'
import { useNavPending } from '@/components/site/NavPendingContext'
import { hasPortalRouteCachedPreview } from '@/lib/portal/portalRouteCachePreview'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

function PortalNavPendingBar() {
  return (
    <div
      className="portal-nav-pending-bar pointer-events-none absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden"
      role="progressbar"
      aria-hidden
    >
      <div className="portal-nav-pending-bar__fill h-full bg-v-terracotta" />
    </div>
  )
}

/**
 * Zone main portail : preview stale si cache destination, sinon conserver l’écran
 * courant pendant la transition (G4-B1). Skeleton réservé aux écrans sans contenu.
 */
export function PortalShellMain({ children, className }: Props) {
  const { isNavigating, effectivePath, showPendingBar } = useNavPending()
  const hasPreview = isNavigating && hasPortalRouteCachedPreview(effectivePath)
  const mode = resolvePortalShellMainNavMode(isNavigating, hasPreview)

  return (
    <div className={cn('relative flex flex-1 flex-col', className)}>
      {showPendingBar ? <PortalNavPendingBar /> : null}

      {mode === 'preview' ? (
        <div className="pointer-events-none flex flex-1 flex-col" aria-busy="true" aria-live="polite">
          <PortalRouteCachedPreview route={effectivePath} className="flex flex-1 flex-col" />
        </div>
      ) : null}

      <div
        className={cn(
          'flex flex-1 flex-col',
          mode === 'preview' && 'hidden',
          mode === 'keep-children' && 'pointer-events-none',
        )}
        aria-busy={mode === 'keep-children' || undefined}
        aria-live={mode === 'keep-children' ? 'polite' : undefined}
      >
        {children}
      </div>
    </div>
  )
}
