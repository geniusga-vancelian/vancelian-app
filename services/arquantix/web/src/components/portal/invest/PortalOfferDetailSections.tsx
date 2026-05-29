'use client'

import { PortalDsImageCarousel } from '@/components/portal/invest/PortalDsImageCarousel'
import { PortalVaultModuleWeb } from '@/components/portal/invest/vault/PortalVaultModuleWeb'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { ExclusiveOfferVaultPayload, VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import type { PortalOfferAsideView, PortalOfferHeroView } from '@/lib/portal/offerDetailFormat'

/** Hero carousel — handoff `.dh-article` · `.carousel__progress`. */
export function PortalOfferHero({ hero }: { hero: PortalOfferHeroView }) {
  return (
    <PortalDsImageCarousel photos={hero.photos} variant="hero" ariaLabel="Visuel de l'offre">
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
              Clôture · {hero.closingLabel}
            </span>
          ) : null}
        </div>
        <h1 className="dh-article__title">{hero.title}</h1>
      </div>
    </PortalDsImageCarousel>
  )
}

/** Conseil advisor — réutilisé par les pages panier / bundle. */
export function PortalOfferAdvisorCard({ text }: { text: string }) {
  return (
    <section className="ai-tip">
      <div className="ai-tip__icon" aria-hidden="true">
        <KalaiIcon name="info" size={16} />
      </div>
      <div className="ai-tip__body">
        <h3 className="ai-tip__title">Le conseil de votre advisor</h3>
        <p className="ai-tip__text">{text}</p>
      </div>
    </section>
  )
}

/** Corps de page — modules Vault Builder via le routeur DS portail (`ofd-*`). */
export function PortalOfferVaultModules({
  modules,
  headerImageUrl,
  lending,
}: {
  modules: VaultModulePublic[]
  headerImageUrl: string | null
  lending: ExclusiveOfferVaultPayload['lending']
}) {
  const enabledModules = modules.filter((mod) => mod.enabled !== false)
  if (!enabledModules.length) return null
  const ctx = { headerImageUrl, lending }

  return (
    <>
      {enabledModules.map((mod) => (
        <section key={mod.id} className="ofd-section ofd-vault-module">
          <PortalVaultModuleWeb mod={mod} ctx={ctx} />
        </section>
      ))}
    </>
  )
}

export function PortalOfferAside({
  aside,
  onInvest,
}: {
  aside: PortalOfferAsideView
  onInvest: () => void
}) {
  return (
    <aside className="ofd-aside">
      <div className="ofd-aside__card">
        {aside.yearlyReturn ? (
          <>
            <span className="ofd-aside__label">Rendement annuel cible</span>
            <span className="ofd-aside__big">{aside.yearlyReturn}</span>
          </>
        ) : null}

        <div className="ofd-aside__rows">
          {aside.ticket ? (
            <div>
              <span className="k">Ticket</span>
              <span className="v">{aside.ticket}</span>
            </div>
          ) : null}
          {aside.term ? (
            <div>
              <span className="k">Durée</span>
              <span className="v">{aside.term}</span>
            </div>
          ) : null}
          {aside.closingLabel ? (
            <div>
              <span className="k">Clôture</span>
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
              {aside.investors != null ? ` · ${aside.investors} investisseurs` : ''}
            </span>
          </div>
        ) : null}

        <button type="button" className="btn btn--primary btn--lg ofd-aside__cta" onClick={onInvest}>
          Investir
        </button>
        <a href="/app/profile" className="ofd-aside__link">
          Poser une question à votre advisor
        </a>
      </div>
    </aside>
  )
}

export function PortalOfferStickyCta({
  aside,
  onInvest,
}: {
  aside: PortalOfferAsideView
  onInvest: () => void
}) {
  return (
    <div className="ofd-stick">
      <div className="ofd-stick__inner">
        <div className="ofd-stick__meta">
          {aside.yearlyReturn ? <span className="ofd-stick__k">{aside.yearlyReturn}/an</span> : null}
          {aside.ticket ? <span className="ofd-stick__sub">Ticket {aside.ticket}</span> : null}
        </div>
        <button type="button" className="btn btn--primary btn--lg ofd-stick__cta" onClick={onInvest}>
          Investir
        </button>
      </div>
    </div>
  )
}

export function PortalOfferInvestPanel({ onClose }: { onClose: () => void }) {
  return (
    <div className="ofd-invest-panel">
      <div className="ofd-section">
        <h2 className="ofd-section__title">Investir dans cette offre</h2>
        <p className="ofd-narrative__prose">
          La souscription en ligne sera bientôt disponible. En attendant, contactez votre advisor pour
          finaliser votre investissement.
        </p>
        <PortalAdvisorBanner />
        <div className="ofd-narrative__actions">
          <button type="button" className="btn btn--secondary" onClick={onClose}>
            Retour à l&apos;offre
          </button>
          <a href="/app/profile" className="btn btn--primary">
            Contacter mon advisor
          </a>
        </div>
      </div>
    </div>
  )
}
