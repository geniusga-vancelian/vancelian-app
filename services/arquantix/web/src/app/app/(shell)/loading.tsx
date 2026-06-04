'use client'

import { usePathname } from 'next/navigation'

import { PortalRouteCachedPreview } from '@/components/portal/PortalRouteCachedPreview'
import { PortalRouteSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { hasPortalRouteCachedPreview } from '@/lib/portal/portalRouteCachePreview'

/**
 * Transition URL-first entre onglets shell : preview stale si cache, sinon skeleton destination.
 * Le pathname reflète déjà la route cible (Next router = source de vérité).
 */
export default function PortalShellSegmentLoading() {
  const pathname = usePathname() ?? '/app/dashboard'

  if (hasPortalRouteCachedPreview(pathname)) {
    return <PortalRouteCachedPreview route={pathname} className="flex flex-1 flex-col" />
  }

  return <PortalRouteSkeleton route={pathname} />
}
