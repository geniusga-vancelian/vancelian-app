'use client'

import dynamic from 'next/dynamic'
import { PortalMarketsSectionSkeleton } from '@/components/portal/PortalRouteSkeleton'

export const PortalMarketsNewsSectionLazy = dynamic(
  () =>
    import('@/components/portal/markets/PortalMarketsNewsSection').then((m) => ({
      default: m.PortalMarketsNewsSection,
    })),
  { ssr: false, loading: () => <PortalMarketsSectionSkeleton /> },
)

export const PortalResearchSectionLazy = dynamic(
  () =>
    import('@/components/portal/markets/PortalResearchSection').then((m) => ({
      default: m.PortalResearchSection,
    })),
  { ssr: false, loading: () => <PortalMarketsSectionSkeleton variant="compact" /> },
)

export const PortalMarketsSidebarLazy = dynamic(
  () =>
    import('@/components/portal/markets/PortalMarketsSidebar').then((m) => ({
      default: m.PortalMarketsSidebar,
    })),
  { ssr: false, loading: () => <PortalMarketsSectionSkeleton variant="sidebar" /> },
)
