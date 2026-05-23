'use client'

import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { cn } from '@/lib/utils'

type PortalLogoutOverlayProps = {
  /** `below-topnav` : filtre le contenu sous le menu. `fullscreen` : toute la page. */
  variant?: 'fullscreen' | 'below-topnav'
  className?: string
}

/** Voile immédiat pendant la déconnexion — feedback visuel avant redirect login. */
export function PortalLogoutOverlay({
  variant = 'fullscreen',
  className,
}: PortalLogoutOverlayProps) {
  const belowTopnav = variant === 'below-topnav'

  return (
    <div
      className={cn(
        'fixed left-0 right-0',
        belowTopnav ? 'z-40' : 'inset-0 z-[200]',
        'cursor-wait bg-v-bg/60 backdrop-blur-[6px]',
        'pointer-events-auto',
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
