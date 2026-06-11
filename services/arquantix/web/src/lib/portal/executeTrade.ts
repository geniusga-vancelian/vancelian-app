/**
 * Primitive trade LI.FI unifiée (ADR 008) — même rail que le swap portail :
 * confirm (re-quote) → sign → submit → poll terminal.
 */
import { bundleLegConfirmAndPrepare, type BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import { recordSwapFailure } from '@/lib/portal/swapClient'
import { classifySwapError, executionPhaseToFailurePhase, SwapExecutionError } from '@/lib/portal/swapFailure'
import type { SwapExecutePayload } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type ExecuteTradeDeps = {
  signAndSubmit: (exec: SwapExecutePayload) => Promise<string>
  pollUntilTerminal: (swapId: string) => Promise<{ status: string; tx_hash?: string | null }>
  onPhaseChange?: (phase: SwapExecutionPhase) => void
}

export type ExecuteTradeResult = {
  swapId: string
  txHash?: string | null
  terminalStatus: string
}

export async function executeTrade(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps: ExecuteTradeDeps,
): Promise<ExecuteTradeResult> {
  let phase: SwapExecutionPhase = 'verifying_price'
  try {
    const exec = await bundleLegConfirmAndPrepare(swapId, snapshot, {
      onPhaseChange: (p) => {
        phase = p
        deps.onPhaseChange?.(p)
      },
    })
    deps.onPhaseChange?.('signing')
    phase = 'signing'
    const txHash = await deps.signAndSubmit(exec)
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

/** @deprecated Utiliser executeTrade — alias conservé 1 sprint. */
export const executeBundleTrade = executeTrade
export type ExecuteBundleTradeDeps = ExecuteTradeDeps
export type ExecuteBundleTradeResult = ExecuteTradeResult
