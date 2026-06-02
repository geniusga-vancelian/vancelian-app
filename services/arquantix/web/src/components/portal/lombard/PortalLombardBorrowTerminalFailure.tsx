'use client'

import { LOMBARD_TERMINAL_FAILURE_COPY } from '@/lib/portal/lombard/lombardProcessingUx'

type Props = {
  onRetry: () => void
  onClose: () => void
  retryDisabled?: boolean
}

export function PortalLombardBorrowTerminalFailure({
  onRetry,
  onClose,
  retryDisabled = false,
}: Props) {
  return (
    <div className="rounded-xl border border-v-error/30 bg-v-error/5 p-4">
      <p className="m-0 font-ui text-[16px] font-medium text-v-error">
        {LOMBARD_TERMINAL_FAILURE_COPY.title}
      </p>
      {LOMBARD_TERMINAL_FAILURE_COPY.lines.map((line) => (
        <p key={line} className="m-0 mt-2 font-ui text-[14px] text-v-fg">
          {line}
        </p>
      ))}
      <div className="brw-foot mt-4">
        <button type="button" className="btn btn--ghost btn--lg" onClick={onClose}>
          Fermer
        </button>
        <button
          type="button"
          className="btn btn--primary btn--lg brw-foot__cta"
          disabled={retryDisabled}
          onClick={onRetry}
        >
          Réessayer
        </button>
      </div>
    </div>
  )
}
