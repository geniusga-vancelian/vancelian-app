'use client'

import type { ReactNode } from 'react'
import { PortalRouteSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { useNavPending } from '@/components/site/NavPendingContext'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/**
 * Zone main portail : au clic menu, bascule immédiatement sur le skeleton
 * de la page cible (plus de fade opacity sur l’ancienne page).
 */
export function PortalShellMain({ children, className }: Props) {
  const { isNavigating, effectivePath } = useNavPending()

  if (isNavigating) {
    return (
      <div className={cn('flex flex-1 flex-col', className)} aria-busy="true" aria-live="polite">
        <PortalRouteSkeleton route={effectivePath} />
      </div>
    )
  }

  return <div className={cn('flex flex-1 flex-col', className)}>{children}</div>
}
