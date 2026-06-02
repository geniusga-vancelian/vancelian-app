'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { TransactionResultPageProps } from '@/components/portal/transaction/types'

export function TransactionResultPage(props: TransactionResultPageProps) {
  if (props.variant === 'impossible') {
    const {
      copy,
      onRetry,
      onClose,
      retryDisabled = false,
      closeLabel = 'Fermer',
      retryLabel = 'Réessayer',
    } = props
    return (
      <div className="rounded-xl border border-v-error/30 bg-v-error/5 p-4">
        <p className="m-0 font-ui text-[16px] font-medium text-v-error">{copy.title}</p>
        {copy.lines.map((line) => (
          <p key={line} className="m-0 mt-2 font-ui text-[14px] text-v-fg">
            {line}
          </p>
        ))}
        <div className="brw-foot mt-4">
          <button type="button" className="btn btn--ghost btn--lg" onClick={onClose}>
            {closeLabel}
          </button>
          <button
            type="button"
            className="btn btn--primary btn--lg brw-foot__cta"
            disabled={retryDisabled}
            onClick={onRetry}
          >
            {retryLabel}
          </button>
        </div>
      </div>
    )
  }

  const {
    title,
    lead,
    subtitle,
    steps,
    summary,
    note,
    primaryAction,
    onClose,
    cardClassName = 'brw brw-succ v-card',
    layout = 'full',
  } = props

  const isCompact = layout === 'compact'

  return (
    <div className={cardClassName}>
      {onClose ? (
        <button
          type="button"
          className="inv-head__btn brw-dismiss"
          aria-label="Fermer"
          onClick={onClose}
          style={{ width: 32 }}
        >
          <KalaiIcon name="close" size={16} />
        </button>
      ) : null}

      <div className="brw-succ__hero">
        <span className="brw-succ__badge" aria-hidden>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <h3 className="brw-succ__title">{title}</h3>
        <p className="brw-succ__lead">{lead}</p>
        {isCompact && subtitle ? <p className="brw-succ__lead m-0 mt-2 text-v-fg-muted">{subtitle}</p> : null}
      </div>

      {isCompact ? (
        <div className="brw-foot brw-succ__foot">
          <button type="button" className="btn btn--primary btn--lg brw-foot__cta" onClick={primaryAction.onClick}>
            {primaryAction.icon}
            {primaryAction.label}
          </button>
        </div>
      ) : null}

      {!isCompact ? (
        <>
      <section className="txn-step brw-succ__step">
        <h2 className="txn-step__title">Étapes de votre emprunt</h2>
        <ol className="txn-step__list">
          {steps.map((step, i) => (
            <li key={step.name} className="txn-step__item">
              <span className="txn-step__badge" aria-hidden>
                {i + 1}
              </span>
              <div className="txn-step__body">
                <h3 className="txn-step__name">{step.name}</h3>
                {step.body}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="txn-sum brw-succ__sum">
        <h2 className="txn-sum__title">Récapitulatif</h2>
        <div className="txn-sum__list">
          {summary.map((row) => (
            <div className="txn-sum__row" key={row.k}>
              <span className="txn-sum__k">{row.k}</span>
              <span className="txn-sum__v v-tnum">{row.v}</span>
            </div>
          ))}
        </div>
      </section>

      {note ? <p className="brw-succ__note">{note}</p> : null}

      <div className="brw-foot brw-succ__foot">
        <button type="button" className="btn btn--primary btn--lg brw-foot__cta" onClick={primaryAction.onClick}>
          {primaryAction.icon}
          {primaryAction.label}
        </button>
      </div>
        </>
      ) : null}
    </div>
  )
}
