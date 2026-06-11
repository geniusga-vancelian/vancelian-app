'use client'

import { resolveTransactionStepMarkerState } from '@/components/portal/transaction/transactionStepper'
import type {
  TransactionStep,
  TransactionStepMarkerState,
} from '@/components/portal/transaction/types'

type Props = {
  steps: TransactionStep[]
  progressIndex: number
  completedProgressIndex: number
  stepStates?: TransactionStepMarkerState[]
  className?: string
}

export function TransactionStepList({
  steps,
  progressIndex,
  completedProgressIndex,
  stepStates,
  className = 'stepper brw-proc__stepper',
}: Props) {
  return (
    <div className={className}>
      {steps.map((step, i) => {
        const st = resolveTransactionStepMarkerState(
          i,
          progressIndex,
          completedProgressIndex,
          stepStates?.[i],
        )
        return (
          <div className="step" key={step.label}>
            {st === 'done' ? (
              <span className="marker marker--done" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            ) : null}
            {st === 'loading' ? (
              <span className="marker marker--current" aria-label="En cours" />
            ) : null}
            {st === 'failed' ? (
              <span className="marker marker--failed" aria-label="Échec">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </span>
            ) : null}
            {st === 'pending' ? <span className="marker marker--pending" aria-hidden /> : null}
            <div className="step__body">
              <div
                className={`step__title${
                  st === 'pending' ? ' dim' : st === 'failed' ? ' step__title--failed' : ''
                }`}
              >
                {step.label}
                {st === 'loading' ? <span className="tag">En cours</span> : null}
                {st === 'failed' ? <span className="tag tag--failed">Échec</span> : null}
              </div>
              <p className="step__sub">{step.subtext}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
