'use client'

import { useMemo } from 'react'

import {
  PortalOfferAside,
  PortalOfferHero,
  PortalOfferStickyCta,
  PortalOfferVaultModules,
} from '@/components/portal/invest/PortalOfferDetailSections'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  buildPortalOfferAsideView,
  buildPortalOfferHeroView,
} from '@/lib/portal/offerDetailFormat'
import {
  PORTAL_ROUTES,
  portalVaultInvestRoute,
  resolvePortalVaultEngineInvestRoute,
} from '@/lib/portal/portalRouting'

type Props = {
  payload: ExclusiveOfferVaultPayload
}

/** Exclusive offer detail — handoff Offre.html (`ofd-grid` · `ofd-main` · vault modules). */
export function PortalOfferDetailScreen({ payload }: Props) {
  const hero = useMemo(() => buildPortalOfferHeroView(payload), [payload])
  const aside = useMemo(() => buildPortalOfferAsideView(payload), [payload])
  const contentModules = useMemo(() => {
    if (!hero.heroCarouselModuleId) return payload.contentModules
    return payload.contentModules.filter((mod) => mod.id !== hero.heroCarouselModuleId)
  }, [payload.contentModules, hero.heroCarouselModuleId])
  const investHref = payload.vaultEngine
    ? resolvePortalVaultEngineInvestRoute(payload.vaultEngine, payload.pageSlug, 'invest')
    : portalVaultInvestRoute(payload.pageSlug)
  const withdrawHref = payload.vaultEngine
    ? resolvePortalVaultEngineInvestRoute(payload.vaultEngine, payload.pageSlug, 'withdraw')
    : portalVaultInvestRoute(payload.pageSlug, 'withdraw')

  return (
    <PortalPageContainer className="ofd-page">
      <PortalDetailBackLink href={PORTAL_ROUTES.invest} label="Back to offers" />

      <div className="ofd-grid">
        <div className="ofd-main">
          <PortalOfferHero hero={hero} />
          <PortalOfferVaultModules
            modules={contentModules}
            headerImageUrl={hero.photos[0] ?? payload.headerImageUrl}
            lending={payload.lending}
          />
          <p className="ofd-note">
            Need more detail? Your advisor is available in under a minute.
          </p>
        </div>

        <PortalOfferAside aside={aside} investHref={investHref} withdrawHref={withdrawHref} />
      </div>

      <PortalOfferStickyCta aside={aside} investHref={investHref} withdrawHref={withdrawHref} />
    </PortalPageContainer>
  )
}
