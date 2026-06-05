'use client'

import { TransactionResultPage } from '@/components/portal/transaction/TransactionResultPage'
import { LOMBARD_TERMINAL_FAILURE_COPY } from '@/components/portal/transaction/mappers/lombardSteps'
import type { TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'

type Props = {
  onRetry: () => void
  onClose: () => void
  retryDisabled?: boolean
  copy?: TransactionTerminalFailureCopy
}

/** Lombard terminal failure — délégué à TransactionResultPage (R4.5-B). */
export function PortalLombardBorrowTerminalFailure({
  onRetry,
  onClose,
  retryDisabled = false,
  copy = LOMBARD_TERMINAL_FAILURE_COPY,
}: Props) {
  return (
    <TransactionResultPage
      variant="impossible"
      copy={copy}
      onRetry={onRetry}
      onClose={onClose}
      retryDisabled={retryDisabled}
    />
  )
}
