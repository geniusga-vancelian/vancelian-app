'use client'

import { transactionProcessingStepperState } from '@/components/portal/transaction/transactionStepper'
import type { TransactionStep } from '@/components/portal/transaction/types'

type Props = {
  steps: TransactionStep[]
  progressIndex: number
  completedProgressIndex: number
  className?: string
}

export function TransactionStepList({
  steps,
  progressIndex,
  completedProgressIndex,
  className = 'stepper brw-proc__stepper',
}: Props) {
  return (
    <div className={className}>
      {steps.map((step, i) => {
        const st = transactionProcessingStepperState(i, progressIndex, completedProgressIndex)
        return (
          <div className="step" key={step.label}>
            {st === 'done' ? (
              <span className="marker marker--done" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            ) : null}
            {st === 'current' ? <span className="marker marker--current" aria-label="En cours" /> : null}
            {st === 'pending' ? <span className="marker marker--pending" aria-hidden /> : null}
            <div className="step__body">
              <div className={`step__title${st === 'pending' ? ' dim' : ''}`}>
                {step.label}
                {st === 'current' ? <span className="tag">En cours</span> : null}
              </div>
              <p className="step__sub">{step.subtext}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
