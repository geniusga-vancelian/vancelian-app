'use client'

import { useMemo, useState } from 'react'

import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import {
  PortalOfferAdvisorCard,
  PortalOfferExtraModules,
  PortalOfferFaqSection,
  PortalOfferHero,
  PortalOfferInvestPanel,
  PortalOfferLocationSection,
  PortalOfferMetricsSection,
  PortalOfferNarrativeSection,
  PortalOfferOverviewSection,
  PortalOfferResourcesSection,
  PortalOfferStickyCta,
  PortalOfferTimelineSection,
  PortalOfferWhySection,
  PortalOfferAside,
} from '@/components/portal/invest/PortalOfferDetailSections'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { buildPortalOfferDetailView } from '@/lib/portal/offerDetailFormat'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  payload: ExclusiveOfferVaultPayload
}

/** Détail offre exclusive — handoff Offre.html (`ofd-*` · `portal-placer-grid`). */
export function PortalOfferDetailScreen({ payload }: Props) {
  const view = useMemo(() => buildPortalOfferDetailView(payload), [payload])
  const [investOpen, setInvestOpen] = useState(false)

  return (
    <PortalPageContainer className="ofd-page">
      <PortalDetailBackLink
        href={investOpen ? '#' : PORTAL_ROUTES.invest}
        label={investOpen ? "Retour à l'offre" : 'Retour aux offres'}
        onClick={
          investOpen
            ? (e) => {
                e.preventDefault()
                setInvestOpen(false)
              }
            : undefined
        }
      />

      <PortalPortfolioLayout
        main={
          investOpen ? (
            <PortalOfferInvestPanel onClose={() => setInvestOpen(false)} />
          ) : (
            <>
              <PortalOfferHero view={view} />
              {view.advisorText ? <PortalOfferAdvisorCard text={view.advisorText} /> : null}
              <PortalOfferMetricsSection view={view} />
              <PortalOfferWhySection view={view} />
              <PortalOfferOverviewSection view={view} />
              <PortalOfferLocationSection view={view} />
              <PortalOfferNarrativeSection view={view} />
              <PortalOfferTimelineSection view={view} />
              <PortalOfferExtraModules view={view} />
              <PortalOfferFaqSection view={view} />
              <PortalOfferResourcesSection view={view} />
              <p className="ofd-note">
                Si vous souhaitez en savoir plus, contactez votre advisor — il est joignable en moins
                d&apos;une minute.
              </p>
            </>
          )
        }
        side={!investOpen ? <PortalOfferAside view={view} onInvest={() => setInvestOpen(true)} /> : undefined}
      />

      {!investOpen ? <PortalOfferStickyCta view={view} onInvest={() => setInvestOpen(true)} /> : null}
    </PortalPageContainer>
  )
}
