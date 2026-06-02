'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import {
  isLombardOpeningPhase,
  LOMBARD_PROCESSING_STEPS,
  lombardProcessingStepperIndex,
  lombardProcessingStepperState,
  resolveProcessingStepSubtext,
} from '@/lib/portal/lombard/lombardProcessingUx'
import { parseBorrowAmountInput, formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'

type Props = {
  recap: LombardBorrowRecap
  executionPhase: LombardExecutionPhase
  openingSubtextTick?: number
  onClose: () => void
}

export function PortalLombardBorrowProcessing({
  recap,
  executionPhase,
  openingSubtextTick = 0,
  onClose,
}: Props) {
  const progressIndex = lombardProcessingStepperIndex(executionPhase)
  const borrowLabel =
    recap.borrowAmountLabel ||
    formatBorrowAmountFr(parseBorrowAmountInput(recap.borrowAmount), 2)
  const showOpeningRotation = isLombardOpeningPhase(executionPhase)

  return (
    <div className="brw brw-proc v-card">
      <button
        type="button"
        className="inv-head__btn brw-dismiss"
        aria-label="Fermer"
        onClick={onClose}
        style={{ width: 32 }}
      >
        <KalaiIcon name="close" size={16} />
      </button>

      <div className="brw-proc__head">
        <h3 className="brw__title">Transaction en cours</h3>
        <p className="brw__lead">
          Votre emprunt de <b className="v-tnum">{borrowLabel} USDC</b> est en cours de traitement.
          Ne fermez pas cette fenêtre.
        </p>
      </div>

      <div className="stepper brw-proc__stepper">
        {LOMBARD_PROCESSING_STEPS.map((step, i) => {
          const st = lombardProcessingStepperState(i, progressIndex)
          const sub =
            i === 2 && showOpeningRotation
              ? resolveProcessingStepSubtext({
                  stepIndex: i,
                  recap,
                  openingSubtextTick,
                })
              : step.defaultSub(recap)
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
                <p className="step__sub">{sub}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
