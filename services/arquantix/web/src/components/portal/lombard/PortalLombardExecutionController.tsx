'use client'

import { useEffect, useRef } from 'react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'
import {
  LombardTerminalBorrowError,
  usePortalLombardExecution,
} from '@/lib/portal/usePortalLombardExecution'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalLombardExecutionRequest = {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
}

type Props = {
  request: PortalLombardExecutionRequest
  /** Incrémenté à chaque tentative (continue ou retry) pour relancer l’effet. */
  runId: number
  requiresPrivySigning: boolean
  onPhaseChange: (phase: LombardExecutionPhase) => void
  onInvisibleRetry: () => void
  onSuccess: () => void
  onTerminalFailure: () => void
  onExecutingChange: (executing: boolean) => void
}

/** open_loan Lombard — signer + retry invisible ; Web3 lazy au processing (R4.5-F6). */
function PortalLombardExecutionRunner({
  request,
  runId,
  requiresPrivySigning,
  onPhaseChange,
  onInvisibleRetry,
  onSuccess,
  onTerminalFailure,
  onExecutingChange,
}: Props) {
  const { privyReady } = usePortalAuthPrivy()
  const privyReadyRef = useRef(privyReady)
  const { executeOpenLoan } = usePortalLombardExecution()

  useEffect(() => {
    privyReadyRef.current = privyReady
  }, [privyReady])

  useEffect(() => {
    let cancelled = false
    onExecutingChange(true)
    onPhaseChange('preparing')

    void (async () => {
      try {
        if (requiresPrivySigning) {
          await waitForPrivyClientReady(() => privyReadyRef.current, { timeoutMs: 30_000 })
        }
        await executeOpenLoan({
          collateral: request.collateral,
          borrowAmount: request.borrowAmount,
          walletAddress: request.walletAddress,
          targetLtvPercent: request.targetLtvPercent,
          onPhaseChange: (phase) => {
            if (!cancelled) onPhaseChange(phase)
          },
          onInvisibleRetry: () => {
            if (!cancelled) onInvisibleRetry()
          },
        })
        if (!cancelled) onSuccess()
      } catch (error) {
        if (cancelled) return
        if (error instanceof LombardTerminalBorrowError) {
          onTerminalFailure()
          return
        }
        onTerminalFailure()
      } finally {
        if (!cancelled) onExecutingChange(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [
    executeOpenLoan,
    onExecutingChange,
    onInvisibleRetry,
    onPhaseChange,
    onSuccess,
    onTerminalFailure,
    request.borrowAmount,
    request.collateral,
    request.targetLtvPercent,
    request.walletAddress,
    requiresPrivySigning,
    runId,
  ])

  return null
}

export function PortalLombardExecutionController(props: Props) {
  return (
    <PortalWeb3BoundaryLazy>
      <PortalLombardExecutionRunner {...props} />
    </PortalWeb3BoundaryLazy>
  )
}
