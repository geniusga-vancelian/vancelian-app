'use client'

import { useEffect, useRef, useState } from 'react'

import { VaultModuleWeb } from '@/components/exclusive-offer/VaultModuleWeb'
import { PortalOfferAdvisorCard } from '@/components/portal/invest/PortalOfferDetailSections'
import { PortalVaultMarkdownContent } from '@/components/portal/invest/vault/PortalVaultMarkdownContent'
import {
  PortalVaultAllocation,
  PortalVaultBlogALaUne,
  PortalVaultBulletList,
  PortalVaultMarketingCards,
  PortalVaultMarketingLargePortrait,
  PortalVaultMediaCarousel,
  PortalVaultNumberedList,
  PortalVaultPerformanceChart,
  PortalVaultQuote,
  PortalVaultTransactions,
  PortalVaultVideos,
  PortalVaultVirtualVisualization,
} from '@/components/portal/invest/vault/PortalVaultExtendedModules'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  isAdvisorMarkdownModule,
  normVaultModuleType,
  readCompetitiveAdvantages,
  readDocumentResources,
  readFaqItems,
  readKeyInformationMetrics,
  readMarkdownModule,
  readParagraphText,
  readStepsTimeline,
  type PortalVaultMetricRow,
  type PortalVaultTimelineStep,
} from '@/lib/portal/vaultModulePortalFormat'
import { cn } from '@/lib/utils'

const COVER_GRAD =
  'linear-gradient(160deg, #1a2840 0%, #38597d 40%, #c7d4e3 100%)'

const PILLAR_ICONS = ['star', 'globe', 'check'] as const

type PortalVaultContext = {
  headerImageUrl: string | null
  lending: ExclusiveOfferVaultPayload['lending']
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
          <button type="button" className="stat__tip__close" aria-label="Fermer" onClick={() => setOpen(false)}>
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      ) : null}
    </div>
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
          <h3 className="faq__title">{item.q}</h3>
          <span className="faq__toggle" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14" />
            </svg>
          </span>
        </div>
        <p className="faq__body">{item.a}</p>
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
      <h3 className="faq__title">{item.q}</h3>
      <span className="faq__toggle" aria-hidden>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </span>
    </div>
  )
}

function timelineMarker(state: PortalVaultTimelineStep['state']) {
  if (state === 'done') {
    return (
      <span className="marker marker--done" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    )
  }
  if (state === 'current') {
    return <span className="marker marker--current" aria-label="En cours" />
  }
  return <span className="marker marker--pending" aria-hidden="true" />
}

function SectionTitle({ title, action }: { title: string; action?: React.ReactNode }) {
  if (action) {
    return (
      <div className="ofd-section__head">
        <h2 className="ofd-section__title">{title}</h2>
        {action}
      </div>
    )
  }
  return <h2 className="ofd-section__title">{title}</h2>
}

function PortalVaultKeyInformation({ mod }: { mod: VaultModulePublic }) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Informations clés'
  const metrics = readKeyInformationMetrics(mod.content)
  if (!metrics.length) return null
  return (
    <>
      <SectionTitle title={title || 'Informations clés'} />
      <div className="stats stats--lined">
        {metrics.map((row, i) => (
          <MetricStatRow key={`${row.key}-${i}`} row={row} />
        ))}
      </div>
    </>
  )
}

function PortalVaultFunding({ mod, ctx }: { mod: VaultModulePublic; ctx: PortalVaultContext }) {
  const resolved = mod.content._resolved as Record<string, unknown> | null | undefined
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

  return (
    <>
      {typeof mod.content.title === 'string' && mod.content.title.trim() ? (
        <SectionTitle title={mod.content.title.trim()} />
      ) : null}
      <div className="funding">
        <div
          className="funding__media"
          style={
            coverUrl ? { backgroundImage: `url('${coverUrl}')` } : { background: COVER_GRAD }
          }
        />
        <div className="funding__body">
          <div className="funding__lead">
            <b>{raised}</b>
            <span className="muted">&nbsp;levés sur {target}</span>
          </div>
          <div className="funding__bar">
            <span style={{ width: `${pct}%` }} />
          </div>
          <div className="funding__meta">
            <span />
            <span>
              <b>{pct} %</b>&nbsp;atteints
            </span>
          </div>
        </div>
      </div>
    </>
  )
}

function PortalVaultCompetitiveAdvantages({ mod }: { mod: VaultModulePublic }) {
  const { title, items } = readCompetitiveAdvantages(mod.content)
  if (!items.length) return null
  return (
    <>
      {title ? <SectionTitle title={title} /> : null}
      <div className="pillars">
        {items.map((it, i) => (
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
    </>
  )
}

function PortalVaultSteps({ mod }: { mod: VaultModulePublic }) {
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : ''
  const steps = readStepsTimeline(mod.content)
  if (!steps.length) return null
  return (
    <>
      <SectionTitle title={title || "Calendrier de l'opération"} />
      <div className="stepper">
        {steps.map((s, i) => (
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
    </>
  )
}

function PortalVaultFaq({ mod }: { mod: VaultModulePublic }) {
  const [openIdx, setOpenIdx] = useState(0)
  const title = typeof mod.content.title === 'string' ? mod.content.title.trim() : 'Questions fréquentes'
  const faq = readFaqItems(mod.content)
  const footerLabel =
    typeof mod.content.footerLinkLabel === 'string' ? mod.content.footerLinkLabel.trim() : ''
  const footerHref =
    typeof mod.content.footerLinkUrl === 'string' ? mod.content.footerLinkUrl.trim() : ''
  if (!faq.length) return null

  return (
    <>
      <SectionTitle
        title={title}
        action={
          footerLabel && footerHref ? (
            <a href={footerHref} className="ofd-section__see">
              {footerLabel}
            </a>
          ) : undefined
        }
      />
      <div className="faq">
        {faq.map((it, i) => (
          <FaqRow
            key={i}
            item={it}
            open={openIdx === i}
            onToggle={() => setOpenIdx(openIdx === i ? -1 : i)}
          />
        ))}
      </div>
    </>
  )
}

function PortalVaultDocuments({ mod }: { mod: VaultModulePublic }) {
  const title =
    typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : 'Ressources'
  const resources = readDocumentResources(mod.content)
  if (!resources.length) return null
  return (
    <>
      <SectionTitle title={title} />
      <div className="docs">
        {resources.map((r, i) => (
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
    </>
  )
}

function PortalVaultLocalisation({ mod }: { mod: VaultModulePublic }) {
  const c = mod.content
  const title = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : 'Localisation'
  const address = typeof c.description === 'string' ? c.description.trim() : ''
  const embedUrl = typeof c.embedUrl === 'string' ? c.embedUrl.trim() : ''
  if (!address && !embedUrl) return null

  return (
    <>
      <SectionTitle title={title} />
      <div className="map-card">
        <div className={cn('map', embedUrl && 'map--embed')}>
          {embedUrl ? (
            <iframe
              title="Carte"
              src={embedUrl}
              className="map__iframe"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          ) : (
            <>
              <div className="map__grid" aria-hidden />
              <div className="map__mini" aria-hidden />
            </>
          )}
        </div>
        <div className="map-card__body">
          <h3 className="map-card__title">Adresse</h3>
          {address ? <p className="map-card__sub">{address}</p> : null}
        </div>
      </div>
    </>
  )
}

function PortalVaultMarkdown({ mod }: { mod: VaultModulePublic }) {
  const { moduleTitle, markdown, links } = readMarkdownModule(mod.content)
  if (!markdown) return null

  if (isAdvisorMarkdownModule(mod)) {
    return <PortalOfferAdvisorCard text={markdown} />
  }

  const hasLinks = links.some((l) => l?.label && l?.url)
  if (hasLinks) {
    return (
      <div className="ofd-narrative">
        {moduleTitle ? <SectionTitle title={moduleTitle} /> : null}
        <PortalVaultMarkdownContent markdown={markdown} variant="narrative" />
        <div className="ofd-narrative__actions">
          {links.map((l, i) =>
            l?.label && l?.url ? (
              <a key={i} href={l.url} className={i === 0 ? 'btn btn--primary' : 'btn btn--secondary'}>
                {l.label}
              </a>
            ) : null,
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      {moduleTitle ? <SectionTitle title={moduleTitle} /> : null}
      <div className="overview">
        <PortalVaultMarkdownContent markdown={markdown} variant="overview" />
      </div>
    </>
  )
}

function PortalVaultParagraph({ mod }: { mod: VaultModulePublic }) {
  const text = readParagraphText(mod.content)
  if (!text) return null
  return (
    <div className="overview">
      <PortalVaultMarkdownContent markdown={text} variant="overview" />
    </div>
  )
}

function PortalVaultHeading({ mod }: { mod: VaultModulePublic }) {
  const text = typeof mod.content.text === 'string' ? mod.content.text.trim() : ''
  if (!text) return null
  return <h2 className="ofd-section__title">{text}</h2>
}

function PortalVaultLegalFooter({ mod }: { mod: VaultModulePublic }) {
  const markdown = typeof mod.content.markdown === 'string' ? mod.content.markdown.trim() : ''
  if (!markdown) return null
  return <PortalVaultMarkdownContent markdown={markdown} variant="narrative" />
}

/** Types rendus avec le DS portail (`ofd-*` / App DS). Fallback site uniquement pour types inconnus. */
export const PORTAL_NATIVE_VAULT_MODULE_TYPES = new Set([
  'keyinformationmodule',
  'fundingmodule',
  'competitiveadvantagesmodule',
  'stepsmodule',
  'faqaccordionmodule',
  'documentslistmodule',
  'localisationmodule',
  'simplemarkdowncontentmodule',
  'paragraph',
  'heading',
  'contentbasdepagesansmoduleblanc',
  'blogalaune',
  'blog_a_la_une',
  'mediaimagecarouselmodule',
  'allocationmodule',
  'performancechart',
  'transactionlatest10module',
  'marktingcardlargeportrait',
  'marketingcardssmallcarouselmodule',
  'marketingcardssmallslidingcarrousel_portrait',
  'marketingcardssmallslidingcarrousel_paysage',
  'videoblockarticlemodule',
  'virtualvisualizationmodule',
  'quote',
  'bullet_list',
  'numbered_list',
])

type Props = {
  mod: VaultModulePublic
  ctx: PortalVaultContext
}

/**
 * Routeur Vault Builder portail — mappe chaque module vers le handoff `ofd-*`
 * (Offre.html) au lieu du DS site public (`VaultModuleWeb`).
 */
export function PortalVaultModuleWeb({ mod, ctx }: Props) {
  const type = normVaultModuleType(mod.type)

  switch (type) {
    case 'keyinformationmodule':
      return <PortalVaultKeyInformation mod={mod} />
    case 'fundingmodule':
      return <PortalVaultFunding mod={mod} ctx={ctx} />
    case 'competitiveadvantagesmodule':
      return <PortalVaultCompetitiveAdvantages mod={mod} />
    case 'stepsmodule':
      return <PortalVaultSteps mod={mod} />
    case 'faqaccordionmodule':
      return <PortalVaultFaq mod={mod} />
    case 'documentslistmodule':
      return <PortalVaultDocuments mod={mod} />
    case 'localisationmodule':
      return <PortalVaultLocalisation mod={mod} />
    case 'simplemarkdowncontentmodule':
      return <PortalVaultMarkdown mod={mod} />
    case 'paragraph':
      return <PortalVaultParagraph mod={mod} />
    case 'heading':
      return <PortalVaultHeading mod={mod} />
    case 'contentbasdepagesansmoduleblanc':
      return <PortalVaultLegalFooter mod={mod} />
    case 'blogalaune':
    case 'blog_a_la_une':
      return <PortalVaultBlogALaUne mod={mod} />
    case 'mediaimagecarouselmodule':
      return <PortalVaultMediaCarousel mod={mod} />
    case 'allocationmodule':
      return <PortalVaultAllocation mod={mod} />
    case 'performancechart':
      return <PortalVaultPerformanceChart mod={mod} />
    case 'transactionlatest10module':
      return <PortalVaultTransactions mod={mod} />
    case 'marktingcardlargeportrait':
      return <PortalVaultMarketingLargePortrait mod={mod} />
    case 'marketingcardssmallcarouselmodule':
      return <PortalVaultMarketingCards mod={mod} />
    case 'marketingcardssmallslidingcarrousel_portrait':
      return <PortalVaultMarketingCards mod={mod} portrait />
    case 'marketingcardssmallslidingcarrousel_paysage':
      return <PortalVaultMarketingCards mod={mod} />
    case 'videoblockarticlemodule':
      return <PortalVaultVideos mod={mod} />
    case 'virtualvisualizationmodule':
      return <PortalVaultVirtualVisualization mod={mod} />
    case 'quote':
      return <PortalVaultQuote mod={mod} />
    case 'bullet_list':
      return <PortalVaultBulletList mod={mod} />
    case 'numbered_list':
      return <PortalVaultNumberedList mod={mod} />
    default:
      return <VaultModuleWeb mod={mod} />
  }
}

export function usesPortalVaultRenderer(mod: VaultModulePublic): boolean {
  return PORTAL_NATIVE_VAULT_MODULE_TYPES.has(normVaultModuleType(mod.type))
}
