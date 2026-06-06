'use client'

import { useEffect, useRef, useState } from 'react'

import { PortalVaultMarkdownContent } from '@/components/portal/invest/vault/PortalVaultMarkdownContent'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  readKeyInformationMetrics,
  shouldShowVaultMetricsFundingStrip,
  type PortalVaultMetricRow,
} from '@/lib/portal/vaultModulePortalFormat'

const COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

type PortalVaultContext = {
  headerImageUrl: string | null
  lending: ExclusiveOfferVaultPayload['lending']
}

export function PortalOfferAdvisorCard({ text }: { text: string }) {
  return (
    <section className="ai-tip">
      <div className="ai-tip__icon" aria-hidden="true">
        <KalaiIcon name="info" size={16} />
      </div>
      <div className="ai-tip__body">
        <h3 className="ai-tip__title">Your advisor&apos;s take</h3>
        <PortalVaultMarkdownContent markdown={text} variant="advisor" />
      </div>
    </section>
  )
}

function MetricStatRow({ row }: { row: PortalVaultMetricRow }) {
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
    <div ref={wrapRef} className={`stat${open ? ' stat--open' : ''}`}>
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
            aria-label={`Learn more about ${row.key}`}
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
          <button type="button" className="stat__tip__close" aria-label="Close" onClick={() => setOpen(false)}>
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      ) : null}
    </div>
  )
}

function FundingStrip({
  ctx,
  fundingMod,
}: {
  ctx: PortalVaultContext
  fundingMod: VaultModulePublic | null
}) {
  const resolved = fundingMod?.content._resolved as Record<string, unknown> | null | undefined
  if (!resolved && !ctx.lending) return null

  const pct = ctx.lending
    ? Math.min(100, Math.max(0, Math.round(ctx.lending.progressPct)))
    : Math.min(
        100,
        Math.max(
          0,
          Math.round(
            typeof resolved?.progressPct === 'number'
              ? resolved.progressPct
              : Number.parseFloat(String(resolved?.progressPct ?? 0)),
          ),
        ),
      )
  const raised = ctx.lending?.raised ?? '—'
  const target =
    ctx.lending?.target ??
    (typeof resolved?.totalDisplay === 'string' ? resolved.totalDisplay : '—')
  const coverUrl = ctx.headerImageUrl
  const investors =
    typeof resolved?.investorsCount === 'number'
      ? resolved.investorsCount
      : typeof resolved?.investors === 'number'
        ? resolved.investors
        : null

  return (
    <div className="funding">
      <div
        className="funding__media"
        style={coverUrl ? { backgroundImage: `url('${coverUrl}')` } : { background: COVER_GRAD }}
      />
      <div className="funding__body">
        <div className="funding__lead">
          <b>{raised}</b>
          <span className="muted">&nbsp;raised of {target}</span>
        </div>
        <div className="funding__bar">
          <span style={{ width: `${pct}%` }} />
        </div>
        <div className="funding__meta">
          {investors != null ? (
            <span className="invs">
              <KalaiIcon name="user-group" size={16} aria-hidden />
              <b>{investors}</b>&nbsp;investors
            </span>
          ) : (
            <span />
          )}
          <span>
            <b>{pct} %</b>&nbsp;funded
          </span>
        </div>
      </div>
    </div>
  )
}

/** Key information — handoff `OfferMetrics` (funding strip + `.stats--lined`). */
export function PortalOfferMetricsSection({
  keyMod,
  fundingMod,
  ctx,
}: {
  keyMod: VaultModulePublic | null
  fundingMod: VaultModulePublic | null
  ctx: PortalVaultContext
}) {
  const title =
    (typeof keyMod?.content.title === 'string' && keyMod.content.title.trim()) ||
    (typeof fundingMod?.content.title === 'string' && fundingMod.content.title.trim()) ||
    'Key information'

  const metrics = keyMod ? readKeyInformationMetrics(keyMod.content) : []
  const hasFunding = shouldShowVaultMetricsFundingStrip(fundingMod)
  if (!metrics.length && !hasFunding) return null

  return (
    <section className="ofd-section">
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">{title}</h2>
      </div>
      {hasFunding ? <FundingStrip ctx={ctx} fundingMod={fundingMod} /> : null}
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
