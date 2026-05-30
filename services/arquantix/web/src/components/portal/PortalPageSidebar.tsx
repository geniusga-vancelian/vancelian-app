'use client'

import {
  SupportAsidePanel,
  hasSupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalPlacerBanner } from '@/components/portal/invest/PortalPlacerView'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import type { PortalExclusiveOffer } from '@/lib/portal/investTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type PortalPageSidebarProps = {
  /** Carte portrait advisor (handoff `.adv-A`) — activée sur emprunt / portfolio. */
  showPortrait?: boolean
  /** Bannière offre (handoff `FeaturedCard` / `.mkt`) — portfolio, emprunt. */
  showFeatured?: boolean
  featuredOffer?: PortalExclusiveOffer | null
}

/** Offre mise en avant sidebar — aligné handoff Portfolio.html (Niseko). */
export const PORTAL_SIDEBAR_FEATURED_OFFER: PortalExclusiveOffer = {
  id: 'sidebar-niseko',
  slug: 'niseko-mori-lodge',
  title: 'The beauty of Japan',
  subtitle: 'Niseko Hokkaidō Lodge · Mountain hospitality, 6.2% yield',
  coverUrl: '/app-ds/assets/photos/niseko-entrance.jpg',
  category: 'Real estate',
  categorySlug: 'immobilier',
  description: '',
  progressPct: 0,
  raisedLabel: '',
  targetLabel: '',
  investorsCount: 0,
  apyLabel: '6.2%',
  durationMonths: null,
  isFunded: false,
  href: PORTAL_ROUTES.invest,
}

/** Colonne droite portail — modules communs (advisor, FAQ CMS, offre). */
export function PortalPageSidebar({
  showPortrait = true,
  showFeatured = false,
  featuredOffer = null,
}: PortalPageSidebarProps) {
  const cmsSupport = usePortalSupportContent()
  const showSupportAside = hasSupportAsideContent(cmsSupport)
  const featured = featuredOffer ?? (showFeatured ? PORTAL_SIDEBAR_FEATURED_OFFER : null)

  return (
    <>
      {showPortrait ? <PortalAdvisorPortraitCard /> : null}
      <PortalAdvisorBanner />
      {showFeatured && featured ? <PortalPlacerBanner offer={featured} /> : null}
      {showSupportAside && !showFeatured ? (
        <SupportAsidePanel support={cmsSupport} stickyTopClassName="static" className="static" />
      ) : null}
    </>
  )
}
