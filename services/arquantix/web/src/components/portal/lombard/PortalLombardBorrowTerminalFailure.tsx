'use client'

import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import { LOMBARD_TERMINAL_FAILURE_COPY } from '@/components/portal/transaction/mappers/lombardSteps'

type Props = {
  onRetry: () => void
  onClose: () => void
  retryDisabled?: boolean
}

/** Lombard terminal failure — délégué à TransactionResultPage (R4.5-B). */
export function PortalLombardBorrowTerminalFailure({
  onRetry,
  onClose,
  retryDisabled = false,
}: Props) {
  return (
    <TransactionResultPage
      variant="impossible"
      copy={LOMBARD_TERMINAL_FAILURE_COPY}
      onRetry={onRetry}
      onClose={onClose}
      retryDisabled={retryDisabled}
    />
  )
}
