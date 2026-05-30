'use client'

import type { MouseEvent, ReactNode } from 'react'

import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalInvestFlowPanel } from '@/components/portal/invest/PortalInvestFlowDom'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  backHref?: string
  backLabel?: string
  onBackClick?: () => void
  children: ReactNode
}

/** Swap flow layout — same grid as vault invest (panel + advisor sidebar). */
export function PortalSwapLayout({
  backHref = PORTAL_ROUTES.cryptoWallet,
  backLabel = 'Back to wallet',
  onBackClick,
  children,
}: Props) {
  const handleBack = onBackClick
    ? (event: MouseEvent<HTMLAnchorElement>) => {
        event.preventDefault()
        onBackClick()
      }
    : undefined

  return (
    <PortalPageContainer className="inv-page">
      <div className="portal-placer-grid">
        <div className="col-main placer-invest">
          <PortalDetailBackLink href={backHref} label={backLabel} onClick={handleBack} />
          <PortalInvestFlowPanel>{children}</PortalInvestFlowPanel>
        </div>

        <aside className="col-side" aria-label="Advisor and help">
          <PortalAdvisorPortraitCard />
          <PortalAdvisorBanner />
        </aside>
      </div>
    </PortalPageContainer>
  )
}
