/**
 * Un leg LI.FI = un swap portail (ADR 008) :
 * confirm (re-quote) → sign → submit → poll terminal.
 * Même rail que PortalSwapExecutionController.runExecution.
 */
import { bundleLegConfirmAndPrepare, type BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import { recordSwapFailure } from '@/lib/portal/swapClient'
import { classifySwapError, executionPhaseToFailurePhase, SwapExecutionError } from '@/lib/portal/swapFailure'
import type { SwapExecutePayload } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type PortalSwapLegDeps = {
  signAndSubmit: (exec: SwapExecutePayload, fromAsset?: string) => Promise<string>
  pollUntilTerminal: (swapId: string) => Promise<{ status: string; tx_hash?: string | null }>
  onPhaseChange?: (phase: SwapExecutionPhase) => void
}

export type PortalSwapLegResult = {
  swapId: string
  txHash?: string | null
  terminalStatus: string
}

export async function runPortalSwapLeg(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  fromAsset: string,
  deps: PortalSwapLegDeps,
): Promise<PortalSwapLegResult> {
  let phase: SwapExecutionPhase = 'verifying_price'
  try {
    const exec = await bundleLegConfirmAndPrepare(swapId, snapshot, {
      onPhaseChange: (p) => {
        phase = p
        deps.onPhaseChange?.(p)
      },
    })
    if (!exec.transaction) {
      throw new SwapExecutionError({
        code: 'lifi_error',
        failurePhase: 'signing',
        technicalMessage: 'Payload transaction manquant',
      })
    }
    deps.onPhaseChange?.('signing')
    phase = 'signing'
    const txHash = await deps.signAndSubmit(exec, fromAsset)
    deps.onPhaseChange?.('submitting')
    phase = 'submitting'
    const terminal = await deps.pollUntilTerminal(swapId)
    if (terminal.status !== 'CONFIRMED') {
      throw new SwapExecutionError({
        code: terminal.status === 'EXPIRED' ? 'quote_expired' : 'unknown_error',
        failurePhase: 'polling',
        technicalMessage: `Swap non confirmé (${terminal.status})`,
      })
    }
    deps.onPhaseChange?.('completed')
    return {
      swapId,
      txHash,
      terminalStatus: terminal.status,
    }
  } catch (err) {
    if (!(err instanceof SwapExecutionError)) {
      const classified = classifySwapError(err, executionPhaseToFailurePhase(phase))
      try {
        await recordSwapFailure(swapId, {
          failure_phase: classified.failurePhase,
          error_code: classified.code,
          technical_message: classified.technicalMessage,
        })
      } catch {
        // best-effort
      }
      throw classified
    }
    throw err
  }
}
