'use client'

import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import {
  isLombardOpeningPhase,
  LOMBARD_PROCESSING_COMPLETED_INDEX,
  LOMBARD_PROCESSING_STEPS,
  lombardProcessingStepperIndex,
  resolveLombardProcessingStepSubtext,
} from '@/components/portal/transaction/mappers/lombardSteps'
import type { LombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import { parseBorrowAmountInput, formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'

type Props = {
  recap: LombardBorrowRecap
  executionPhase: LombardExecutionPhase
  openingSubtextTick?: number
  onClose: () => void
}

/** Lombard borrow processing — délégué à TransactionProcessingPage (R4.5-B). */
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

  const steps = LOMBARD_PROCESSING_STEPS.map((step, i) => ({
    label: step.label,
    subtext:
      i === 2 && showOpeningRotation
        ? resolveLombardProcessingStepSubtext({
            stepIndex: i,
            recap,
            openingSubtextTick,
          })
        : step.defaultSub(recap),
  }))

  return (
    <TransactionProcessingPage
      title="Transaction en cours"
      lead={
        <>
          Votre emprunt de <b className="v-tnum">{borrowLabel} USDC</b> est en cours de traitement.
          Ne fermez pas cette fenêtre.
        </>
      }
      steps={steps}
      progressIndex={progressIndex}
      completedProgressIndex={LOMBARD_PROCESSING_COMPLETED_INDEX}
      onClose={onClose}
    />
  )
}
