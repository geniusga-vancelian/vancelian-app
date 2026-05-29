'use client'

import type { ReactNode } from 'react'
import dynamic from 'next/dynamic'
import { PortalRouteSkeleton } from '@/components/portal/PortalRouteSkeleton'

const PortalRouteCachedPreview = dynamic(
  () =>
    import('@/components/portal/PortalRouteCachedPreview').then((m) => m.PortalRouteCachedPreview),
  { loading: () => null },
)
import { useNavPending } from '@/components/site/NavPendingContext'
import { hasPortalRouteCachedPreview } from '@/lib/portal/portalRouteCachePreview'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/**
 * Zone main portail : cache stale pendant la navigation si disponible,
 * sinon skeleton immédiat.
 */
export function PortalShellMain({ children, className }: Props) {
  const { isNavigating, effectivePath } = useNavPending()

  if (isNavigating) {
    if (hasPortalRouteCachedPreview(effectivePath)) {
      return <PortalRouteCachedPreview route={effectivePath} className={className} />
    }

    return (
      <div className={cn('flex flex-1 flex-col', className)} aria-busy="true" aria-live="polite">
        <PortalRouteSkeleton route={effectivePath} />
      </div>
    )
  }

  return <div className={cn('flex flex-1 flex-col', className)}>{children}</div>
}
