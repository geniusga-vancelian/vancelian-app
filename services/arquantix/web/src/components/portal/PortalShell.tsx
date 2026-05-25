'use client'

import type { ReactNode } from 'react'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { PortalTopnav } from '@/components/portal/PortalTopnav'
import { PersistentSiteFooter } from '@/components/site/PersistentSiteFooter'
import { PortalShellMain } from '@/components/portal/PortalShellMain'
import { NavPendingProvider } from '@/components/site/NavPendingContext'
import { warmAllPortalMainRoutes } from '@/lib/portal/portalNavWarmup'
import type { SiteBrandLogo } from '@/components/ui/BrandLogo'
import type { SiteFooterData } from '@/lib/cms/site-footer'
import type { PortalSupportContent } from '@/lib/cms/portal-support'
import { getDefaultPortalSupportContent } from '@/lib/cms/portal-support'
import { PortalSupportContentProvider } from '@/components/portal/PortalSupportContentProvider'
import { PortalChainProvider } from '@/lib/portal/portalChainContext'
import { PortalWalletScopeProvider } from '@/lib/portal/portalWalletScopeContext'
import { TOPNAV_HEIGHT_PX } from '@/hooks/useTopnavSurfaceObserver'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { preloadPrivyPortalProvider } from '@/lib/portal/preloadPrivyPortalProvider'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  initials?: string
  brand?: SiteBrandLogo | null
  initialFooterData?: SiteFooterData
  initialSupportContent?: PortalSupportContent
}

/** Coque portail : topnav + contenu + footer persistants entre navigations. */
export function PortalShell({
  children,
  className,
  initials,
  brand,
  initialFooterData,
  initialSupportContent,
}: Props) {
  const router = useRouter()

  useEffect(() => {
    router.prefetch(PORTAL_ROUTES.login)
    preloadPrivyPortalProvider()

    const warm = () => warmAllPortalMainRoutes(router)
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(warm, { timeout: 4000 })
    } else {
      window.setTimeout(warm, 800)
    }
  }, [router])

  return (
    <PortalSupportContentProvider
      content={initialSupportContent ?? getDefaultPortalSupportContent()}
    >
      <NavPendingProvider>
        <PortalChainProvider>
          <PortalWalletScopeProvider>
            <div className="flex min-h-screen flex-col bg-v-bg">
              <PortalTopnav initials={initials} brand={brand} />
              <main
                className={cn('flex w-full flex-1 flex-col', className)}
                style={{ paddingTop: TOPNAV_HEIGHT_PX }}
              >
                <PortalShellMain className="flex flex-1 flex-col">{children}</PortalShellMain>
              </main>
              <PersistentSiteFooter initialData={initialFooterData} />
            </div>
          </PortalWalletScopeProvider>
        </PortalChainProvider>
      </NavPendingProvider>
    </PortalSupportContentProvider>
  )
}
