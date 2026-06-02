'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { TransactionStepList } from '@/components/portal/transaction/TransactionStepList'
import type { TransactionProcessingPageProps } from '@/components/portal/transaction/types'

export function TransactionProcessingPage({
  title,
  lead,
  steps,
  progressIndex,
  completedProgressIndex,
  onClose,
  cardClassName = 'brw brw-proc v-card',
}: TransactionProcessingPageProps) {
  return (
    <div className={cardClassName}>
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
        <h3 className="brw__title">{title}</h3>
        <p className="brw__lead">{lead}</p>
      </div>

      <TransactionStepList
        steps={steps}
        progressIndex={progressIndex}
        completedProgressIndex={completedProgressIndex}
      />
    </div>
  )
}
