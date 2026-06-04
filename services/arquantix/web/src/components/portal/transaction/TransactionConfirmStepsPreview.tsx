'use client'

import { useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { TransactionStep } from '@/components/portal/transaction/types'

type Props = {
  steps: TransactionStep[]
  title?: string
  className?: string
}

/** Accordéon « Étapes de la transaction » — preview avant signature (handoff InvestConfirm). */
export function TransactionConfirmStepsPreview({
  steps,
  title = 'Étapes de la transaction',
  className = 'txn-step inv-confirm__steps',
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <section className={className}>
      <button
        type="button"
        className="txn-step__toggle txn-step__sectoggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <h2 className="txn-step__title">
          {title} <span className="txn-step__count">{steps.length} étapes</span>
        </h2>
        <span className="txn-step__chev" data-open={open ? 'true' : undefined}>
          <KalaiIcon name="chevron-down" size={16} />
        </span>
      </button>
      {open ? (
        <ol className="txn-step__list txn-step__detail">
          {steps.map((step, i) => (
            <li key={step.label} className="txn-step__item">
              <span className="txn-step__badge" aria-hidden>
                {i + 1}
              </span>
              <div className="txn-step__body">
                <h3 className="txn-step__name">{step.label}</h3>
                <p className="txn-step__amount">{step.subtext}</p>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  )
}
