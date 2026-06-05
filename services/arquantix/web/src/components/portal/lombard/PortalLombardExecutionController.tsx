'use client'

import { useEffect, useRef } from 'react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'
import { usePortalLombardExecution } from '@/lib/portal/usePortalLombardExecution'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

export type PortalLombardExecutionRequest = {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
  portalWalletCollateralBalance?: string | null
}

type Props = {
  request: PortalLombardExecutionRequest
  /** Incrémenté à chaque tentative (continue ou retry) pour relancer l’effet. */
  runId: number
  /** Mis à true dès que l’open_loan on-chain + confirm backend est terminé (anti-écran erreur fantôme). */
  borrowSucceededRef: React.MutableRefObject<boolean>
  requiresPrivySigning: boolean
  onPhaseChange: (phase: LombardExecutionPhase) => void
  onInvisibleRetry: () => void
  onSuccess: () => void
  onTerminalFailure: (error: unknown) => void
  onExecutingChange: (executing: boolean) => void
}

/** open_loan Lombard — signer + retry invisible ; Web3 lazy au processing (R4.5-F6). */
function PortalLombardExecutionRunner({
  request,
  runId,
  borrowSucceededRef,
  requiresPrivySigning,
  onPhaseChange,
  onInvisibleRetry,
  onSuccess,
  onTerminalFailure,
  onExecutingChange,
}: Props) {
  const { privyReady } = usePortalAuthPrivy()
  const privyReadyRef = useRef(privyReady)
  const openLoanFinishedRef = useRef(false)
  const { executeOpenLoan } = usePortalLombardExecution()

  const onPhaseChangeRef = useRef(onPhaseChange)
  const onInvisibleRetryRef = useRef(onInvisibleRetry)
  const onSuccessRef = useRef(onSuccess)
  const onTerminalFailureRef = useRef(onTerminalFailure)
  const onExecutingChangeRef = useRef(onExecutingChange)
  const executeOpenLoanRef = useRef(executeOpenLoan)

  onPhaseChangeRef.current = onPhaseChange
  onInvisibleRetryRef.current = onInvisibleRetry
  onSuccessRef.current = onSuccess
  onTerminalFailureRef.current = onTerminalFailure
  onExecutingChangeRef.current = onExecutingChange
  executeOpenLoanRef.current = executeOpenLoan

  useEffect(() => {
    privyReadyRef.current = privyReady
  }, [privyReady])

  useEffect(() => {
    if (borrowSucceededRef.current) return

    let cancelled = false
    openLoanFinishedRef.current = false
    onExecutingChangeRef.current(true)
    onPhaseChangeRef.current('preparing')

    void (async () => {
      try {
        if (requiresPrivySigning) {
          await waitForPrivyClientReady(() => privyReadyRef.current, { timeoutMs: 30_000 })
        }
        await executeOpenLoanRef.current({
          collateral: request.collateral,
          borrowAmount: request.borrowAmount,
          walletAddress: request.walletAddress,
          targetLtvPercent: request.targetLtvPercent,
          portalWalletCollateralBalance: request.portalWalletCollateralBalance,
          onPhaseChange: (phase) => {
            if (!cancelled) onPhaseChangeRef.current(phase)
          },
          onInvisibleRetry: () => {
            if (!cancelled) onInvisibleRetryRef.current()
          },
        })
        openLoanFinishedRef.current = true
        borrowSucceededRef.current = true
        if (!cancelled) onSuccessRef.current()
      } catch (error) {
        if (openLoanFinishedRef.current || borrowSucceededRef.current) {
          borrowSucceededRef.current = true
          if (!cancelled) onSuccessRef.current()
          return
        }
        if (cancelled) return
        onTerminalFailureRef.current(error)
      } finally {
        if (!cancelled) onExecutingChangeRef.current(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [
    borrowSucceededRef,
    request.portalWalletCollateralBalance,
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
