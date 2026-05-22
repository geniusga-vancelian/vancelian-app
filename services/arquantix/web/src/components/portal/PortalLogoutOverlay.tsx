'use client'

import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { cn } from '@/lib/utils'

type PortalLogoutOverlayProps = {
  /** `below-topnav` : filtre le contenu sous le menu (logout rapide). */
  variant?: 'fullscreen' | 'below-topnav'
  className?: string
}

/** Voile pendant la déconnexion — menu reste visible et interactif. */
export function PortalLogoutOverlay({
  variant = 'below-topnav',
  className,
}: PortalLogoutOverlayProps) {
  const belowTopnav = variant === 'below-topnav'

  return (
    <div
      className={cn(
        'fixed left-0 right-0',
        belowTopnav ? 'z-40' : 'inset-0 z-[200]',
        'bg-v-bg/55 backdrop-blur-[4px]',
        className,
      )}
      style={belowTopnav ? { top: TOPNAV_HEIGHT_PX, bottom: 0 } : undefined}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Signing out"
    />
  )
}
