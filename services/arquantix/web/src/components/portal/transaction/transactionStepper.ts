import type { TransactionStepperMarkerState } from '@/components/portal/transaction/types'

export function transactionProcessingStepperState(
  stepIndex: number,
  progressIndex: number,
  completedProgressIndex: number,
): TransactionStepperMarkerState {
  if (stepIndex < progressIndex) return 'done'
  if (stepIndex === progressIndex && progressIndex < completedProgressIndex) return 'current'
  return 'pending'
}
