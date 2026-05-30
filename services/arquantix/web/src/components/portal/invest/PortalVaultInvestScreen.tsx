'use client'

import { useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { PortalInvestFlow } from '@/components/portal/invest/PortalInvestFlow'
import { PortalInvestFlowPanel } from '@/components/portal/invest/PortalInvestFlowDom'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalAdvisorPortraitCard } from '@/components/portal/PortalAdvisorPortraitCard'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { buildVaultInvestTarget } from '@/lib/portal/portalInvestFlowFormat'
import { parsePortalVaultFlowMode, portalExclusiveOfferRoute } from '@/lib/portal/portalRouting'

type Props = {
  payload: ExclusiveOfferVaultPayload
}

/** Page investissement vault — handoff Placer invest panel + sidebar advisor. */
export function PortalVaultInvestScreen({ payload }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = parsePortalVaultFlowMode(searchParams?.get('mode') ?? null)
  const offerHref = portalExclusiveOfferRoute(payload.pageSlug)
  const vaultTarget = useMemo(() => buildVaultInvestTarget(payload), [payload])

  return (
    <PortalPageContainer className="inv-page">
      <div className="portal-placer-grid">
        <div className="col-main placer-invest">
          <PortalDetailBackLink href={offerHref} label="Back to offer" />
          <PortalInvestFlowPanel>
            <PortalInvestFlow
              onClose={() => router.push(offerHref)}
              initialTargetKey={payload.pageSlug}
              vaultTarget={vaultTarget}
              initialMode={mode}
            />
          </PortalInvestFlowPanel>
        </div>

        <aside className="col-side" aria-label="Advisor and help">
          <PortalAdvisorPortraitCard />
          <PortalAdvisorBanner />
        </aside>
      </div>
    </PortalPageContainer>
  )
}
