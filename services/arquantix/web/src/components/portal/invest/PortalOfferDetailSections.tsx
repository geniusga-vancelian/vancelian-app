'use client'

import { useEffect, useRef, useState } from 'react'

import { VaultModuleWeb } from '@/components/exclusive-offer/VaultModuleWeb'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { PortalOfferDetailView, PortalOfferMetricRow } from '@/lib/portal/offerDetailFormat'
import { cn } from '@/lib/utils'

type HeroProps = {
  view: PortalOfferDetailView
}

const COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

/** Hero carousel — handoff `.dh-article` · `.carousel__progress`. */
export function PortalOfferHero({ view }: HeroProps) {
  const photos = view.galleryUrls.length ? view.galleryUrls : view.coverUrl ? [view.coverUrl] : []
  const [idx, setIdx] = useState(0)
  const [paused, setPaused] = useState(false)
  const count = photos.length || 1

  useEffect(() => {
    if (paused || count <= 1) return
    const t = window.setInterval(() => setIdx((i) => (i + 1) % count), 5000)
    return () => window.clearInterval(t)
  }, [paused, count])

  const current = photos[idx]

  return (
    <div
      className="carousel dh-article"
      style={{
        backgroundImage: current ? `url('${current}')` : undefined,
        background: !current ? COVER_GRAD : undefined,
      }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {count > 1 ? (
        <div className="carousel__progress" aria-hidden="true">
          {photos.map((_, i) => (
            <button
              key={i}
              type="button"
              className={cn(i < idx && 'on', i === idx && 'playing')}
              onClick={() => setIdx(i)}
              aria-label={`Photo ${i + 1}`}
            />
          ))}
        </div>
      ) : null}
      <div className="dh-article__body">
        <div className="dh-article__chips">
          {view.category ? (
            <span className="dh-article__chip dh-article__chip--terra">
              <span className="dh-article__chip__dot" aria-hidden />
              {view.category}
            </span>
          ) : null}
          {view.closingLabel ? (
            <span className="dh-article__chip">
              <KalaiIcon name="clock" size={16} />
              Clôture · {view.closingLabel}
            </span>
          ) : null}
        </div>
        <h1 className="dh-article__title">{view.title}</h1>
      </div>
    </div>
  )
}

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

function MetricStatRow({ row, index }: { row: PortalOfferMetricRow; index: number }) {
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={wrapRef} className={cn('stat', open && 'stat--open')}>
      <span className="stat__label">
        <span className="lead" aria-hidden="true">
          <KalaiIcon name={row.icon} size={16} />
        </span>
        {row.key}
      </span>
      <span className="stat__value">
        {row.value}
        {row.tip ? (
          <button
            type="button"
            className="stat__info"
            aria-label={`En savoir plus sur ${row.key}`}
            aria-expanded={open}
            onClick={(e) => {
              e.stopPropagation()
              setOpen((v) => !v)
            }}
          >
            <KalaiIcon name="info" size={16} />
          </button>
        ) : null}
      </span>
      {open && row.tip ? (
        <div className="stat__tip" role="tooltip">
          <p className="stat__tip__title">{row.key}</p>
          <p className="stat__tip__body">{row.tip}</p>
          <button
            type="button"
            className="stat__tip__close"
            aria-label="Fermer"
            onClick={() => setOpen(false)}
          >
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      ) : null}
    </div>
  )
}

export function PortalOfferMetricsSection({ view }: { view: PortalOfferDetailView }) {
  const { funding, metrics } = view
  if (!funding && metrics.length === 0) return null

  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">Informations clés</h2>
      </div>

      {funding ? (
        <div className="funding">
          <div
            className="funding__media"
            style={
              funding.coverUrl
                ? { backgroundImage: `url('${funding.coverUrl}')` }
                : { background: COVER_GRAD }
            }
          />
          <div className="funding__body">
            <div className="funding__lead">
              <b>{funding.raised}</b>
              <span className="muted">&nbsp;levés sur {funding.target}</span>
            </div>
            <div className="funding__bar">
              <span style={{ width: `${funding.pct}%` }} />
            </div>
            <div className="funding__meta">
              {funding.investors != null ? (
                <span className="invs">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                    <circle cx="9" cy="8" r="3" />
                    <circle cx="16" cy="9" r="2" />
                    <path d="M3 20c0-3 3-5 6-5s6 2 6 5" />
                    <path d="M14 19c0-2 2-3 4-3s4 1 4 3" />
                  </svg>
                  <b>{funding.investors}</b>&nbsp;investisseurs
                </span>
              ) : (
                <span />
              )}
              <span>
                <b>{funding.pct} %</b>&nbsp;atteints
              </span>
            </div>
          </div>
        </div>
      ) : null}

      {metrics.length > 0 ? (
        <div className="stats stats--lined">
          {metrics.map((row, i) => (
            <MetricStatRow key={`${row.key}-${i}`} row={row} index={i} />
          ))}
        </div>
      ) : null}
    </section>
  )
}

const PILLAR_ICONS = [
  <svg key="0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></svg>,
  <svg key="1" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>,
  <svg key="2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15 8.5 22 9.3 17 14 18.2 21 12 17.8 5.8 21 7 14 2 9.3 9 8.5 12 2" /></svg>,
]

export function PortalOfferWhySection({ view }: { view: PortalOfferDetailView }) {
  if (!view.whyItems.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">{view.whyTitle}</h2>
      <div className="pillars">
        {view.whyItems.map((it, i) => (
          <div className="pillar" key={i}>
            <div className="pillar__icon" aria-hidden="true">
              {PILLAR_ICONS[i % PILLAR_ICONS.length]}
            </div>
            <p className="pillar__text">
              {it.title ? (
                <>
                  <b>{it.title}.</b>{' '}
                </>
              ) : null}
              {it.body}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}

export function PortalOfferOverviewSection({ view }: { view: PortalOfferDetailView }) {
  if (!view.overviewText) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Le bien en détail</h2>
      <div className="overview">
        <h3 className="overview__title">{view.overviewTitle ?? view.title}</h3>
        <p className="overview__body">{view.overviewText}</p>
      </div>
    </section>
  )
}

export function PortalOfferLocationSection({ view }: { view: PortalOfferDetailView }) {
  const loc = view.location
  if (!loc) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">{loc.title}</h2>
      <div className="map-card">
        <div className={cn('map', loc.embedUrl && 'map--embed')}>
          {loc.embedUrl ? (
            <iframe
              title="Carte"
              src={loc.embedUrl}
              className="map__iframe"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          ) : (
            <>
              <div className="map__grid" aria-hidden />
              <div className="map__mini" aria-hidden />
              <div className="map__zoom" aria-hidden>
                <button type="button" tabIndex={-1} aria-label="Zoom in">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
                </button>
                <button type="button" tabIndex={-1} aria-label="Zoom out">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14" /></svg>
                </button>
              </div>
            </>
          )}
        </div>
        <div className="map-card__body">
          <h3 className="map-card__title">Adresse</h3>
          {loc.address ? <p className="map-card__sub">{loc.address}</p> : null}
          {loc.access ? <p className="map-card__sub">{loc.access}</p> : null}
        </div>
      </div>
    </section>
  )
}

export function PortalOfferNarrativeSection({ view }: { view: PortalOfferDetailView }) {
  const narrative = view.narrative
  if (!narrative) return null
  return (
    <section className="ofd-section ofd-narrative">
      <h2 className="ofd-section__title">{narrative.title}</h2>
      <p className="ofd-narrative__prose">{narrative.text}</p>
      {narrative.secondaryCta || narrative.primaryCta ? (
        <div className="ofd-narrative__actions">
          {narrative.secondaryCta ? (
            <a href={narrative.secondaryCta.href} className="btn btn--secondary">
              {narrative.secondaryCta.label}
            </a>
          ) : null}
          {narrative.primaryCta ? (
            <a href={narrative.primaryCta.href} className="btn btn--primary">
              {narrative.primaryCta.label}
            </a>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

function timelineMarker(state: PortalOfferDetailView['timeline'][number]['state']) {
  if (state === 'done') {
    return (
      <span className="marker marker--done" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
      </span>
    )
  }
  if (state === 'current') {
    return <span className="marker marker--current" aria-label="En cours" />
  }
  return <span className="marker marker--pending" aria-hidden="true" />
}

export function PortalOfferTimelineSection({ view }: { view: PortalOfferDetailView }) {
  if (!view.timeline.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Calendrier de l&apos;opération</h2>
      <div className="stepper">
        {view.timeline.map((s, i) => (
          <div className="step" key={i}>
            {timelineMarker(s.state)}
            <div className="step__body">
              <div className={cn('step__title', s.state === 'future' && 'dim')}>
                {s.label}
                {s.chip ? <span className="tag">{s.chip}</span> : null}
              </div>
              {s.sub ? <p className="step__sub">{s.sub}</p> : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function FaqRow({
  item,
  open,
  onToggle,
}: {
  item: { q: string; a: string }
  open: boolean
  onToggle: () => void
}) {
  if (open) {
    return (
      <div className="faq__row is-open" onClick={onToggle} onKeyDown={(e) => e.key === 'Enter' && onToggle()} role="button" tabIndex={0}>
        <div className="faq__head">
          <h3 className="faq__title">{item.q}</h3>
          <span className="faq__toggle" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14" /></svg>
          </span>
        </div>
        <p className="faq__body">{item.a}</p>
      </div>
    )
  }
  return (
    <div className="faq__row" onClick={onToggle} onKeyDown={(e) => e.key === 'Enter' && onToggle()} role="button" tabIndex={0}>
      <h3 className="faq__title">{item.q}</h3>
      <span className="faq__toggle" aria-hidden>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
      </span>
    </div>
  )
}

export function PortalOfferFaqSection({ view }: { view: PortalOfferDetailView }) {
  const [openIdx, setOpenIdx] = useState(0)
  if (!view.faq.length) return null
  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">Questions fréquentes</h2>
        {view.faqFooterHref ? (
          <a href={view.faqFooterHref} className="ofd-section__see">
            {view.faqFooterLabel ?? 'Voir toute la FAQ'}
          </a>
        ) : null}
      </div>
      <div className="faq">
        {view.faq.map((it, i) => (
          <FaqRow
            key={i}
            item={it}
            open={openIdx === i}
            onToggle={() => setOpenIdx(openIdx === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  )
}

export function PortalOfferResourcesSection({ view }: { view: PortalOfferDetailView }) {
  if (!view.resources.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Ressources</h2>
      <div className="docs">
        {view.resources.map((r, i) => (
          <div className="row" key={i}>
            <div className="row__avatar" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6" />
              </svg>
            </div>
            <div className="row__body">
              <h3 className="row__title">{r.name}</h3>
              <p className="row__sub">{r.type} · {r.size}</p>
            </div>
            <div className="row__trailing">
              <a
                href={r.downloadUrl}
                className="icon-btn icon-btn--outline"
                aria-label="Télécharger"
                target="_blank"
                rel="noopener noreferrer"
                download
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 4v12M6 12l6 6 6-6M5 20h14" />
                </svg>
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function PortalOfferExtraModules({ view }: { view: PortalOfferDetailView }) {
  if (!view.extraModules.length) return null
  return (
    <>
      {view.extraModules.map((mod) => (
        <section key={mod.id} className="ofd-section">
          <VaultModuleWeb mod={mod} />
        </section>
      ))}
    </>
  )
}

export function PortalOfferAside({
  view,
  onInvest,
}: {
  view: PortalOfferDetailView
  onInvest: () => void
}) {
  const { aside } = view
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
  view,
  onInvest,
}: {
  view: PortalOfferDetailView
  onInvest: () => void
}) {
  const { aside } = view
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
