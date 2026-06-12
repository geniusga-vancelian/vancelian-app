'use client'

import { useMemo, type ReactNode } from 'react'

import { PortalDsImageCarousel } from '@/components/portal/invest/PortalDsImageCarousel'
import {
  PortalOfferAdvisorCard,
  PortalOfferMetricsSection,
} from '@/components/portal/invest/vault/PortalOfferMetricsSection'
import { PortalVaultModuleWeb } from '@/components/portal/invest/vault/PortalVaultModuleWeb'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { ExclusiveOfferVaultPayload, VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  isAdvisorMarkdownModule,
  normVaultModuleType,
  readMarkdownModule,
} from '@/lib/portal/vaultModulePortalFormat'
import type { PortalOfferAsideView, PortalOfferHeroView } from '@/lib/portal/offerDetailFormat'

export { PortalOfferAdvisorCard }

/** Hero carousel — handoff `.dh-article` · `.carousel__progress`. */
export function PortalOfferHero({ hero }: { hero: PortalOfferHeroView }) {
  return (
    <PortalDsImageCarousel
      photos={hero.photos}
      backgroundVideoUrl={hero.promoVideoUrl}
      variant="hero"
      ariaLabel="Offer hero"
    >
      <div className="dh-article__body">
        <div className="dh-article__chips">
          {hero.category ? (
            <span className="dh-article__chip dh-article__chip--terra">
              <span className="dh-article__chip__dot" aria-hidden />
              {hero.category}
            </span>
          ) : null}
          {hero.closingLabel ? (
            <span className="dh-article__chip">
              <KalaiIcon name="clock" size={16} />
              Closes · {hero.closingLabel}
            </span>
          ) : null}
        </div>
        <h1 className="dh-article__title">{hero.title}</h1>
      </div>
    </PortalDsImageCarousel>
  )
}

type VaultCtx = {
  headerImageUrl: string | null
  lending: ExclusiveOfferVaultPayload['lending']
}

function isMetricsModule(type: string): boolean {
  return type === 'keyinformationmodule' || type === 'fundingmodule'
}

function isNarrativeModule(mod: VaultModulePublic): boolean {
  if (normVaultModuleType(mod.type) !== 'simplemarkdowncontentmodule') return false
  const { links } = readMarkdownModule(mod.content)
  return links.some((l) => l?.label && l?.url)
}

/** Body modules — handoff Offre.html section order and `.ofd-section` grouping. */
export function PortalOfferVaultModules({
  modules,
  headerImageUrl,
  lending,
}: {
  modules: VaultModulePublic[]
  headerImageUrl: string | null
  lending: ExclusiveOfferVaultPayload['lending']
}) {
  const ctx: VaultCtx = { headerImageUrl, lending }
  const enabledModules = modules.filter((mod) => mod.enabled !== false)

  const blocks = useMemo(() => {
    const nodes: ReactNode[] = []
    let index = 0

    while (index < enabledModules.length) {
      const mod = enabledModules[index]!
      const type = normVaultModuleType(mod.type)

      if (isAdvisorMarkdownModule(mod)) {
        nodes.push(<PortalVaultModuleWeb key={mod.id} mod={mod} ctx={ctx} />)
        index += 1
        continue
      }

      if (isMetricsModule(type)) {
        let keyMod: VaultModulePublic | null = null
        let fundingMod: VaultModulePublic | null = null
        while (index < enabledModules.length) {
          const nextType = normVaultModuleType(enabledModules[index]!.type)
          if (nextType === 'keyinformationmodule') {
            keyMod = enabledModules[index]!
            index += 1
          } else if (nextType === 'fundingmodule') {
            fundingMod = enabledModules[index]!
            index += 1
          } else {
            break
          }
        }
        nodes.push(
          <PortalOfferMetricsSection
            key={`metrics-${keyMod?.id ?? fundingMod?.id ?? index}`}
            keyMod={keyMod}
            fundingMod={fundingMod}
            ctx={ctx}
          />,
        )
        continue
      }

      nodes.push(
        <section
          key={mod.id}
          className={isNarrativeModule(mod) ? 'ofd-section ofd-narrative' : 'ofd-section'}
        >
          <PortalVaultModuleWeb mod={mod} ctx={ctx} />
        </section>,
      )
      index += 1
    }

    return nodes
  }, [ctx, enabledModules])

  if (!blocks.length) return null
  return <>{blocks}</>
}

export function PortalOfferAside({
  aside,
  investHref,
  withdrawHref,
}: {
  aside: import('@/lib/portal/offerDetailFormat').PortalOfferAsideView
  investHref: string
  withdrawHref: string
}) {
  return (
    <aside className="ofd-aside">
      <div className="ofd-aside__card">
        {aside.yearlyReturn ? (
          <>
            <span className="ofd-aside__label">Target annual yield</span>
            <span className="ofd-aside__big">{aside.yearlyReturn}</span>
          </>
        ) : null}

        <div className="ofd-aside__rows">
          {aside.ticket ? (
            <div>
              <span className="k">Minimum ticket</span>
              <span className="v">{aside.ticket}</span>
            </div>
          ) : null}
          {aside.term ? (
            <div>
              <span className="k">Term</span>
              <span className="v">{aside.term}</span>
            </div>
          ) : null}
          {aside.closingLabel ? (
            <div>
              <span className="k">Closes</span>
              <span className="v">{aside.closingLabel}</span>
            </div>
          ) : null}
        </div>

        {aside.raised ? (
          <div className="ofd-aside__progress">
            <div className="ofd-progress">
              <span style={{ width: `${aside.pct}%` }} />
            </div>
            <span className="ofd-aside__meta">
              {aside.raised}
              {aside.investors != null ? ` · ${aside.investors} investors` : ''}
            </span>
          </div>
        ) : null}

        <div className="ofd-aside__ctas">
          <PortalNavLink href={investHref} className="btn btn--primary btn--lg ofd-aside__cta">
            Invest
          </PortalNavLink>
          <PortalNavLink href={withdrawHref} className="btn btn--secondary btn--lg ofd-aside__cta">
            Withdraw
          </PortalNavLink>
        </div>
        <a href="/app/profile" className="ofd-aside__link">
          Ask your advisor a question
        </a>
      </div>
    </aside>
  )
}

export function PortalOfferStickyCta({
  aside,
  investHref,
  withdrawHref,
}: {
  aside: PortalOfferAsideView
  investHref: string
  withdrawHref: string
}) {
  return (
    <div className="ofd-stick">
      <div className="ofd-stick__inner">
        <div className="ofd-stick__meta">
          {aside.yearlyReturn ? <span className="ofd-stick__k">{aside.yearlyReturn}/yr</span> : null}
          {aside.ticket ? <span className="ofd-stick__sub">Ticket {aside.ticket}</span> : null}
        </div>
        <div className="ofd-stick__actions">
          <PortalNavLink href={investHref} className="btn btn--primary btn--lg ofd-stick__cta">
            Invest
          </PortalNavLink>
          <PortalNavLink href={withdrawHref} className="btn btn--secondary btn--lg ofd-stick__cta">
            Withdraw
          </PortalNavLink>
        </div>
      </div>
    </div>
  )
}
