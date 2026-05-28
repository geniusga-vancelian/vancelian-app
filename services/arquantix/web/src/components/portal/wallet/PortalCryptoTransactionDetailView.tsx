'use client'

import type { ReactNode } from 'react'
import { AppTxExchangeAvatar } from '@/components/design-system/app/AppTxExchangeAvatar'
import { AppTxFlowAvatar } from '@/components/design-system/app/AppTxFlowAvatar'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import type { PortalCryptoTransactionDetailViewModel } from '@/lib/portal/cryptoTransactionDetailFormat'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  detail: PortalCryptoTransactionDetailViewModel
  backHref: string
  backLabel: string
  sidebar?: ReactNode
}

function TxHeroLeading({ detail }: { detail: PortalCryptoTransactionDetailViewModel }) {
  if (
    (detail.variant === 'swap' || detail.variant === 'borrow') &&
    detail.fromAsset &&
    detail.toAsset
  ) {
    return <AppTxExchangeAvatar fromAsset={detail.fromAsset} toAsset={detail.toAsset} />
  }
  return <AppTxFlowAvatar direction={detail.flowDirection} />
}

function TxStepper({ title, steps }: { title: string; steps: PortalCryptoTransactionDetailViewModel['steps'] }) {
  if (steps.length === 0) return null

  return (
    <section className="txn-step">
      <h2 className="txn-step__title">{title}</h2>
      <ol className="txn-step__list">
        {steps.map((step, index) => (
          <li key={`${step.name}-${index}`} className="txn-step__item">
            <span className="txn-step__badge" aria-hidden>
              {index + 1}
            </span>
            <div className="txn-step__body">
              <h3 className="txn-step__name">{step.name}</h3>
              {step.convert ? (
                <div className="txn-step__convert">
                  <span className="txn-step__from v-tnum">{step.convert.from}</span>
                  <KalaiIcon name="arrow-right" size={16} className="txn-step__arrow" aria-hidden />
                  <span className="txn-step__to v-tnum">{step.convert.to}</span>
                </div>
              ) : null}
              {step.amountLine ? <p className="txn-step__amount">{step.amountLine}</p> : null}
              {step.notes?.length ? (
                <ul className="txn-step__notes">
                  {step.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function TxSummary({ rows }: { rows: PortalCryptoTransactionDetailViewModel['summary'] }) {
  return (
    <section className="txn-sum">
      <h2 className="txn-sum__title">Récapitulatif</h2>
      <div className="txn-sum__list">
        {rows.map((row) => (
          <div key={row.key} className="txn-sum__row">
            <span className="txn-sum__k">{row.key}</span>
            <span className="txn-sum__v v-tnum">{row.value}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function TxStatusTimeline({ detail }: { detail: PortalCryptoTransactionDetailViewModel }) {
  return (
    <div className="txn-stat">
      <div className="txn-stat__head">
        <span className="txn-stat__eyebrow">Statut</span>
        <span className={cn('txn-stat__pill', `txn-stat__pill--${detail.statusTone}`)}>
          <span className="txn-stat__pill-dot" aria-hidden />
          {detail.statusLabel}
        </span>
      </div>
      <ol className="txn-stat__list">
        {detail.timeline.map((item, index) => (
          <li key={`${item.label}-${index}`} className={cn('txn-stat__step', item.done && 'is-done')}>
            <span className="txn-stat__bullet" aria-hidden>
              {item.done ? <KalaiIcon name="check" size={16} /> : null}
            </span>
            <div className="txn-stat__body">
              <span className="txn-stat__label">{item.label}</span>
              <span className="txn-stat__time">{item.time}</span>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

/** Détail transaction — handoff Transaction.html. */
export function PortalCryptoTransactionDetailView({
  detail,
  backHref,
  backLabel,
  sidebar,
}: Props) {
  return (
    <PortalPortfolioLayout
      main={
        <div className="txn-page">
          <PortalDetailBackLink href={backHref} label={backLabel} />

          <header className="txn-hero">
            <div className="txn-hero__top">
              <TxHeroLeading detail={detail} />
              <div className="txn-hero__title-wrap">
                <span className="txn-hero__kind">{detail.kindLabel}</span>
                <h1 className="txn-hero__title">{detail.title}</h1>
              </div>
              <span className={cn('txn-hero__status', `txn-hero__status--${detail.statusTone}`)}>
                <span className="txn-hero__status-dot" aria-hidden />
                {detail.statusLabel}
              </span>
            </div>
            <div className="txn-hero__amount-row">
              <span
                className={cn(
                  'txn-hero__amount v-tnum',
                  detail.amountPositive ? 'is-pos' : 'is-neg',
                )}
              >
                {detail.amountLabel}
              </span>
              <span className="txn-hero__sub">
                {detail.subtitle ? <span>{detail.subtitle}</span> : null}
                <span className="txn-hero__date">{detail.dateLong}</span>
              </span>
            </div>
          </header>

          <TxStepper title={detail.stepperTitle} steps={detail.steps} />
          <TxSummary rows={detail.summary} />

          {detail.counterparty ? (
            <section className="txn-party">
              <h2 className="txn-party__title">Contre-partie</h2>
              <div className="txn-party__row">
                <span className="txn-party__avt" aria-hidden>
                  <KalaiIcon
                    name={detail.flowDirection === 'in' ? 'arrow-down' : 'arrow-up'}
                    size={16}
                  />
                </span>
                <div className="txn-party__body">
                  <span className="txn-party__label">{detail.counterparty.label}</span>
                  <span className="txn-party__sub">{detail.counterparty.sub}</span>
                </div>
              </div>
            </section>
          ) : null}

          <div className="txn-cta">
            <button type="button" className="btn btn--secondary" disabled>
              <KalaiIcon name="download" size={16} aria-hidden />
              Télécharger le reçu
            </button>
            <button type="button" className="btn btn--ghost" disabled>
              <KalaiIcon name="info" size={16} aria-hidden />
              Signaler un problème
            </button>
          </div>
        </div>
      }
      side={
        sidebar ?? (
          <>
            <TxStatusTimeline detail={detail} />
            <PortalAdvisorBanner />
          </>
        )
      }
    />
  )
}
