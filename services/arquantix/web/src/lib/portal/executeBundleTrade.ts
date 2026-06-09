/**
 * Exécution unitaire d'un trade LI.FI bundle — même rail que le swap portail :
 * confirm (re-quote) → sign → submit → poll terminal.
 */
import { bundleLegConfirmAndPrepare, type BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import type { SwapExecutePayload } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type ExecuteBundleTradeDeps = {
  signAndSubmit: (exec: SwapExecutePayload) => Promise<string>
  pollUntilTerminal: (swapId: string) => Promise<{ status: string; tx_hash?: string | null }>
  onPhaseChange?: (phase: SwapExecutionPhase) => void
}

export type ExecuteBundleTradeResult = {
  swapId: string
  txHash?: string | null
  terminalStatus: string
}

export async function executeBundleTrade(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps: ExecuteBundleTradeDeps,
): Promise<ExecuteBundleTradeResult> {
  const exec = await bundleLegConfirmAndPrepare(swapId, snapshot, {
    onPhaseChange: deps.onPhaseChange,
  })
  deps.onPhaseChange?.('signing')
  const txHash = await deps.signAndSubmit(exec)
  deps.onPhaseChange?.('submitting')
  const terminal = await deps.pollUntilTerminal(swapId)
  if (terminal.status !== 'CONFIRMED') {
    throw new Error(`Swap non confirmé (${terminal.status})`)
  }
  deps.onPhaseChange?.('completed')
  return {
    swapId,
    txHash,
    terminalStatus: terminal.status,
  }
}
