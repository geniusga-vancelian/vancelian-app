'use client'

import type { ReactNode } from 'react'

import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalInvestFlowPanel } from '@/components/portal/invest/PortalInvestFlowDom'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  loading?: boolean
  error?: string | null
  onRetry?: () => void
  backHref?: string
  backLabel?: string
  children?: ReactNode
}

/** Layout invest DeFi / bundle — grille handoff Placer (flow + sidebar advisor), aligné swap. */
export function PortalDefiVaultInvestLayout({
  loading,
  error,
  onRetry,
  backHref = PORTAL_ROUTES.invest,
  backLabel = 'Back to vaults',
  children,
}: Props) {
  return (
    <PortalPageContainer className="inv-page">
      <div className="portal-placer-grid">
        <div className="col-main placer-invest">
          <PortalDetailBackLink href={backHref} label={backLabel} />

          {loading ? (
            <p className="m-0 font-ui text-[15px] text-v-fg-muted">Loading vault…</p>
          ) : error ? (
            <div className="space-y-4">
              <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
              {onRetry ? (
                <button
                  type="button"
                  className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
                  onClick={onRetry}
                >
                  Try again
                </button>
              ) : null}
            </div>
          ) : (
            <PortalInvestFlowPanel>{children}</PortalInvestFlowPanel>
          )}
        </div>

        <aside className="col-side" aria-label="Advisor and help">
          <PortalAdvisorPortraitCard />
          <PortalAdvisorBanner />
        </aside>
      </div>
    </PortalPageContainer>
  )
}
