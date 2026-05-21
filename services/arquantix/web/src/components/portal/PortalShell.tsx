'use client'

import type { ReactNode } from 'react'
import { PortalTopnav } from '@/components/portal/PortalTopnav'
import type { SiteBrandLogo } from '@/components/ui/BrandLogo'
import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  initials?: string
  brand?: SiteBrandLogo | null
}

/** Enveloppe portail authentifié — topnav site DS + contenu sous la barre 72px (footer global dans le root layout). */
export function PortalShell({ children, className, initials, brand }: Props) {
  return (
    <div className="bg-v-bg">
      <PortalTopnav initials={initials} brand={brand} />
      <main className={cn('w-full', className)} style={{ paddingTop: TOPNAV_HEIGHT_PX }}>
        {children}
      </main>
    </div>
  )
}
