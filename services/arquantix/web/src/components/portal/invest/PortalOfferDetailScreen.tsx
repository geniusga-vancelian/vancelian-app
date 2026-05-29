'use client'

import { useMemo, useState } from 'react'

import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import {
  PortalOfferAside,
  PortalOfferHero,
  PortalOfferInvestPanel,
  PortalOfferStickyCta,
  PortalOfferVaultModules,
} from '@/components/portal/invest/PortalOfferDetailSections'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  buildPortalOfferAsideView,
  buildPortalOfferHeroView,
} from '@/lib/portal/offerDetailFormat'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  payload: ExclusiveOfferVaultPayload
}

/** Détail offre exclusive — layout portail (`ofd-*`) + contenu Vault Builder + aside invest (temporaire). */
export function PortalOfferDetailScreen({ payload }: Props) {
  const hero = useMemo(() => buildPortalOfferHeroView(payload), [payload])
  const aside = useMemo(() => buildPortalOfferAsideView(payload), [payload])
  const contentModules = useMemo(() => {
    if (!hero.heroCarouselModuleId) return payload.contentModules
    return payload.contentModules.filter((mod) => mod.id !== hero.heroCarouselModuleId)
  }, [payload.contentModules, hero.heroCarouselModuleId])
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
              <PortalOfferHero hero={hero} />
              <PortalOfferVaultModules
                modules={contentModules}
                headerImageUrl={hero.photos[0] ?? payload.headerImageUrl}
                lending={payload.lending}
              />
            </>
          )
        }
        side={!investOpen ? <PortalOfferAside aside={aside} onInvest={() => setInvestOpen(true)} /> : undefined}
      />

      {!investOpen ? <PortalOfferStickyCta aside={aside} onInvest={() => setInvestOpen(true)} /> : null}
    </PortalPageContainer>
  )
}
