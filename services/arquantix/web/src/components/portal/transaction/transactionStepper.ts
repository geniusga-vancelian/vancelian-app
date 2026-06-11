import type {
  TransactionStepMarkerState,
  TransactionStepperMarkerState,
} from '@/components/portal/transaction/types'

export function transactionProcessingStepperState(
  stepIndex: number,
  progressIndex: number,
  completedProgressIndex: number,
): TransactionStepperMarkerState {
  if (stepIndex < progressIndex) return 'done'
  if (stepIndex === progressIndex && progressIndex < completedProgressIndex) return 'current'
  return 'pending'
}

export function resolveTransactionStepMarkerState(
  stepIndex: number,
  progressIndex: number,
  completedProgressIndex: number,
  explicitState?: TransactionStepMarkerState,
): TransactionStepMarkerState {
  if (explicitState) return explicitState
  const legacy = transactionProcessingStepperState(
    stepIndex,
    progressIndex,
    completedProgressIndex,
  )
  if (legacy === 'current') return 'loading'
  return legacy
}
