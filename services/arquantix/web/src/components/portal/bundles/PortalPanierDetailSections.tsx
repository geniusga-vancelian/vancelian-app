'use client'

import { useEffect, useRef, useState } from 'react'

import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalOfferAdvisorCard } from '@/components/portal/invest/PortalOfferDetailSections'
import {
  PortalVaultFaqBodyMarkdown,
  PortalVaultInlineMarkdown,
} from '@/lib/portal/portalVaultInlineMarkdown'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  formatPerfPctLabel,
  type PortalPanierDetailView,
  type PortalPanierMetricRow,
} from '@/lib/portal/bundlePanierDetailFormat'
import {
  CHART_PERIOD_OPTIONS,
  type ChartPeriodId,
} from '@/lib/portal/instrumentDetailFormat'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

const COVER_GRAD =
  'linear-gradient(150deg, #1a1a2e 0%, #2d2d52 45%, #4a4a7c 100%)'

const PILLAR_ICONS = ['star', 'exchange', 'check'] as const

function MetricStatRow({ row }: { row: PortalPanierMetricRow }) {
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

export function PortalPanierHero({ view }: { view: PortalPanierDetailView }) {
  const heroStyle = view.heroImageUrl
    ? { backgroundImage: `url('${view.heroImageUrl}')` }
    : { background: COVER_GRAD }

  return (
    <div className="dh-article cfd-hero" style={heroStyle}>
      <div className="dh-article__body">
        <div className="dh-article__chips">
          <span className="dh-article__chip dh-article__chip--blue">
            <span className="dh-article__chip__dot" aria-hidden />
            {view.category}
          </span>
          {view.perf1yLabel ? (
            <span className="dh-article__chip">
              <KalaiIcon name="trending-up" size={16} />
              {view.perf1yLabel} sur 1 an
            </span>
          ) : null}
          {view.assetCount > 0 ? (
            <span className="dh-article__chip">
              {view.assetCount} actif{view.assetCount > 1 ? 's' : ''}
            </span>
          ) : null}
        </div>
        <h1 className="dh-article__title">{view.title}</h1>
        {view.composition.length > 0 ? (
          <div className="pnr-hero__avatars">
            {view.composition.map((c, i) => (
              <span
                key={c.sym}
                className="pnr-hero__avatar"
                style={{
                  marginLeft: i === 0 ? 0 : -10,
                  zIndex: view.composition.length - i,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={c.icon} alt={c.sym} />
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function PortalPanierMetricsSection({ view }: { view: PortalPanierDetailView }) {
  const { headline, metrics } = view
  const hasHeadline = headline.aum || headline.holders || headline.flow30d
  if (!hasHeadline && metrics.length === 0) return null

  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">Informations clés</h2>
      </div>

      {hasHeadline ? (
        <div className="cfd-headline">
          {headline.aum ? (
            <div className="cfd-headline__cell">
              <span className="cfd-headline__k">Encours</span>
              <span className="cfd-headline__v">{headline.aum}</span>
            </div>
          ) : null}
          {headline.holders ? (
            <div className="cfd-headline__cell">
              <span className="cfd-headline__k">Détenteurs</span>
              <span className="cfd-headline__v">{headline.holders}</span>
            </div>
          ) : null}
          {headline.flow30d ? (
            <div className="cfd-headline__cell">
              <span className="cfd-headline__k">Flux 30 j</span>
              <span className="cfd-headline__v" style={{ color: 'var(--v-green, #33614D)' }}>
                {headline.flow30d}
              </span>
            </div>
          ) : null}
        </div>
      ) : null}

      {metrics.length > 0 ? (
        <div className="stats stats--lined">
          {metrics.map((row, i) => (
            <MetricStatRow key={`${row.key}-${i}`} row={row} />
          ))}
        </div>
      ) : null}
    </section>
  )
}

export function PortalPanierWhySection({ view }: { view: PortalPanierDetailView }) {
  if (!view.whyItems.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">{view.whyTitle}</h2>
      <div className="pillars">
        {view.whyItems.map((it, i) => (
          <div className="pillar" key={i}>
            <div className="pillar__icon" aria-hidden="true">
              <KalaiIcon name={PILLAR_ICONS[i % PILLAR_ICONS.length]} size={16} />
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

export function PortalPanierOverviewSection({ view }: { view: PortalPanierDetailView }) {
  if (!view.overviewText) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Le panier en détail</h2>
      <div className="overview">
        <h3 className="overview__title">{view.overviewTitle}</h3>
        <p className="overview__body">{view.overviewText}</p>
      </div>
    </section>
  )
}

export function PortalPanierCompositionSection({ view }: { view: PortalPanierDetailView }) {
  if (!view.composition.length) return null
  const rebalance = view.rebalanceLabel ?? 'Hebdomadaire'
  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">Composition du panier</h2>
        <span className="cfd-alloc__caption">Rebalancé · {rebalance.toLowerCase()}</span>
      </div>

      <div className="cfd-alloc__stack" role="img" aria-label="Pondération par actif">
        {view.composition.map((a) => (
          <span
            key={a.sym}
            className="cfd-alloc__seg"
            style={{ width: `${a.pct}%`, background: a.color }}
            title={`${a.name} · ${a.pct} %`}
          />
        ))}
      </div>

      <div className="cfd-alloc__rows pnr-comp__rows">
        {view.composition.map((a) => (
          <div className="cfd-alloc__row pnr-comp__row" key={a.sym}>
            <span className="pnr-comp__icon" aria-hidden="true">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={a.icon} alt="" />
            </span>
            <span className="cfd-alloc__name">
              <b>{a.name}</b>
              <span className="cfd-alloc__sub">{a.sym}</span>
            </span>
            <span className="cfd-alloc__pct">
              {a.pct.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

type PerfChartProps = {
  period: ChartPeriodId
  onPeriodChange: (period: ChartPeriodId) => void
  chartPoints: number[]
  chartPerfPct: number | null
  loading: boolean
  error: string | null
}

export function PortalPanierPerformanceSection({
  period,
  onPeriodChange,
  chartPoints,
  chartPerfPct,
  loading,
  error,
}: PerfChartProps) {
  const positive = chartPerfPct == null || chartPerfPct >= 0
  const deltaLabel = formatPerfPctLabel(chartPerfPct)

  return (
    <>
      <section className="cfd-perf ofd-section">
        <div className="cfd-perf__head">
          <h2 className="cfd-perf__title">Performance historique</h2>
          {deltaLabel ? (
            <div className="cfd-perf__delta">
              <span className="cfd-perf__delta-k">Variation</span>
              <span className={cn('cfd-perf__delta-v', positive ? 'text-v-green' : 'text-v-error')}>
                {deltaLabel}
              </span>
            </div>
          ) : null}
        </div>

        <div className="cfd-perf__plot">
          {loading && chartPoints.length === 0 ? (
            <div className="flex h-[200px] items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-v-fg-10 border-t-v-fg" />
            </div>
          ) : error && chartPoints.length === 0 ? (
            <p className="m-0 py-12 text-center font-ui text-[14px] text-v-fg-muted">{error}</p>
          ) : chartPoints.length >= 2 ? (
            <div className={cn('h-[200px]', positive ? 'text-v-green' : 'text-v-error')}>
              <PortalPerformanceChart values={chartPoints} height={200} tone="light" showEndpoint />
            </div>
          ) : (
            <p className="m-0 py-12 text-center font-ui text-[14px] text-v-fg-muted">
              Aucune donnée graphique pour cette plage.
            </p>
          )}
        </div>

        <div className="perf-tabs" role="tablist" aria-label="Plage de temps">
          {CHART_PERIOD_OPTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              className={cn('perf-tabs__tab', period === item.id && 'is-active')}
              aria-selected={period === item.id}
              onClick={() => onPeriodChange(item.id)}
            >
              {item.chip}
            </button>
          ))}
        </div>
      </section>
    </>
  )
}

export function PortalPanierPerfWindowsGrid({
  windows,
}: {
  windows: Array<{ label: string; pct: number | null }>
}) {
  const visible = windows.filter((w) => w.pct != null)
  if (!visible.length) return null
  return (
    <section className="ofd-section" style={{ marginTop: -16 }}>
      <div className="pnr-perf__grid">
        {visible.map((p, i) => {
          const up = (p.pct ?? 0) >= 0
          const formatted = Math.abs(p.pct ?? 0).toLocaleString('fr-FR', {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1,
          })
          return (
            <div className="pnr-perf__cell" key={i}>
              <span className="pnr-perf__k">{p.label}</span>
              <span className={cn('pnr-perf__v', up ? 'is-up' : 'is-down')}>
                {up ? '+ ' : '− '}
                {formatted} %
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function PortalPanierExitsSection({
  view,
  onInvest,
}: {
  view: PortalPanierDetailView
  onInvest: () => void
}) {
  if (!view.exits.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Conditions de sortie</h2>
      {view.exits.map((x, i) => {
        const open = !!x.cta
        return (
          <div className={cn('exit', open ? 'exit--open' : 'exit--closed')} key={i}>
            <div className="exit__avatar" aria-hidden="true">
              <KalaiIcon name="exchange" size={24} />
            </div>
            <div className="exit__body">
              <div className="exit__title-row">
                <h3 className="exit__title">{x.kind}</h3>
                {x.chip ? <span className="exit__fee">{x.chip}</span> : null}
              </div>
              <p className="exit__text">{x.desc}</p>
            </div>
            <span className="exit__info" aria-hidden="true">
              <KalaiIcon name="info" size={16} />
            </span>
            {open ? (
              <button type="button" className="btn btn--primary btn--lg exit__cta" onClick={onInvest}>
                Initier une demande
              </button>
            ) : null}
          </div>
        )
      })}
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
      <div
        className="faq__row is-open"
        onClick={onToggle}
        onKeyDown={(e) => e.key === 'Enter' && onToggle()}
        role="button"
        tabIndex={0}
      >
        <div className="faq__head">
          <h3 className="faq__title">
            <PortalVaultInlineMarkdown text={item.q} />
          </h3>
          <span className="faq__toggle" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14" />
            </svg>
          </span>
        </div>
        <PortalVaultFaqBodyMarkdown text={item.a} />
      </div>
    )
  }
  return (
    <div
      className="faq__row"
      onClick={onToggle}
      onKeyDown={(e) => e.key === 'Enter' && onToggle()}
      role="button"
      tabIndex={0}
    >
      <h3 className="faq__title">
        <PortalVaultInlineMarkdown text={item.q} />
      </h3>
      <span className="faq__toggle" aria-hidden>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </span>
    </div>
  )
}

export function PortalPanierFaqSection({ view }: { view: PortalPanierDetailView }) {
  const [openIdx, setOpenIdx] = useState(0)
  if (!view.faq.length) return null
  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">Questions fréquentes</h2>
        <a href={view.faqFooterHref ?? PORTAL_ROUTES.academy} className="ofd-section__see">
          Voir toute la FAQ
        </a>
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

export function PortalPanierResourcesSection({ view }: { view: PortalPanierDetailView }) {
  if (!view.resources.length) return null
  return (
    <section className="ofd-section">
      <h2 className="ofd-section__title">Ressources et audits</h2>
      <div className="docs">
        {view.resources.map((r, i) => (
          <div className="row" key={i}>
            <div className="row__avatar" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6" />
              </svg>
            </div>
            <div className="row__body">
              <h3 className="row__title">{r.name}</h3>
              <p className="row__sub">
                {r.type} · {r.size}
              </p>
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
                <svg
                  viewBox="0 0 24 24"
                  width="18"
                  height="18"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
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

export function PortalPanierAside({
  view,
  onInvest,
  investLabel,
}: {
  view: PortalPanierDetailView
  onInvest: () => void
  investLabel: string
}) {
  const { aside } = view
  return (
    <aside className="ofd-aside">
      <div className="ofd-aside__card">
        {aside.perfHighlight ? (
          <>
            <span className="ofd-aside__label">Performance 1 an</span>
            <span className="ofd-aside__big">{aside.perfHighlight}</span>
          </>
        ) : null}

        <div className="ofd-aside__rows">
          {aside.ticket ? (
            <div>
              <span className="k">Ticket</span>
              <span className="v">{aside.ticket}</span>
            </div>
          ) : null}
          {aside.fees ? (
            <div>
              <span className="k">Frais</span>
              <span className="v">{aside.fees}</span>
            </div>
          ) : null}
          <div>
            <span className="k">Liquidité</span>
            <span className="v">{aside.liquidity}</span>
          </div>
        </div>

        {aside.aum || aside.holders ? (
          <div className="ofd-aside__progress" style={{ marginTop: 4 }}>
            {aside.aum ? <span className="ofd-aside__meta">Encours · {aside.aum}</span> : null}
            {aside.holders ? (
              <span className="ofd-aside__meta">{aside.holders} détenteurs</span>
            ) : null}
          </div>
        ) : null}

        <button type="button" className="btn btn--primary btn--lg ofd-aside__cta" onClick={onInvest}>
          {investLabel}
        </button>
        <a href={PORTAL_ROUTES.profile} className="ofd-aside__link">
          Poser une question à votre advisor
        </a>
      </div>
    </aside>
  )
}

export function PortalPanierMobileCta({
  view,
  onInvest,
  investLabel,
}: {
  view: PortalPanierDetailView
  onInvest: () => void
  investLabel: string
}) {
  if (!view.aside.perfHighlight) return null
  return (
    <div className="ofd-cta-bar">
      <div className="ofd-cta-bar__inner">
        <div className="ofd-cta-bar__amt">
          <span className="ofd-cta-bar__k">Performance 1 an</span>
          <span className="ofd-cta-bar__v">{view.aside.perfHighlight}</span>
        </div>
        <button type="button" className="btn btn--primary btn--lg" onClick={onInvest}>
          {investLabel}
        </button>
      </div>
    </div>
  )
}
