'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { BrandLogo, type SiteBrandLogo } from '@/components/ui/BrandLogo'
import { isPortalPathname } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type SiteTransitionContextValue = {
  isSiteTransitioning: boolean
  startSiteTransition: () => void
}

const SiteTransitionContext = React.createContext<SiteTransitionContextValue>({
  isSiteTransitioning: false,
  startSiteTransition: () => {},
})

export function useSiteTransition(): SiteTransitionContextValue {
  return React.useContext(SiteTransitionContext)
}

type SiteTransitionProviderProps = {
  brand?: SiteBrandLogo | null
  children: React.ReactNode
}

export function SiteTransitionProvider({ brand, children }: SiteTransitionProviderProps) {
  const pathname = usePathname() ?? ''
  const [isSiteTransitioning, setIsSiteTransitioning] = React.useState(false)

  const startSiteTransition = React.useCallback(() => {
    setIsSiteTransitioning(true)
  }, [])

  React.useEffect(() => {
    if (!isSiteTransitioning) return
    if (isPortalPathname(pathname)) return

    const timer = window.setTimeout(() => setIsSiteTransitioning(false), 350)
    return () => window.clearTimeout(timer)
  }, [isSiteTransitioning, pathname])

  const value = React.useMemo(
    () => ({ isSiteTransitioning, startSiteTransition }),
    [isSiteTransitioning, startSiteTransition],
  )

  return (
    <SiteTransitionContext.Provider value={value}>
      {children}
      <SiteTransitionLoadingOverlay brand={brand} active={isSiteTransitioning} />
    </SiteTransitionContext.Provider>
  )
}

function SiteTransitionLoadingOverlay({
  brand,
  active,
}: {
  brand?: SiteBrandLogo | null
  active: boolean
}) {
  if (!active) return null

  return (
    <div
      className={cn(
        'site-transition-loading fixed inset-0 z-[300]',
        'flex items-center justify-center bg-v-bg',
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Loading Vancelian"
    >
      <BrandLogo
        brand={brand}
        lockup="horizontal"
        color="black"
        className="site-transition-loading__logo h-8 w-auto sm:h-9"
      />
    </div>
  )
}
