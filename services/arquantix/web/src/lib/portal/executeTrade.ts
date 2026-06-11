/**
 * Primitive trade LI.FI unifiée (ADR 008) — délègue à runPortalSwapLeg.
 */
import type { BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import {
  runPortalSwapLeg,
  type PortalSwapLegDeps,
  type PortalSwapLegResult,
} from '@/lib/portal/runPortalSwapLeg'
import type { SwapExecutePayload } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type ExecuteTradeDeps = PortalSwapLegDeps & {
  fromAsset?: string
}

export type ExecuteTradeResult = PortalSwapLegResult

export async function executeTrade(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps: ExecuteTradeDeps,
): Promise<ExecuteTradeResult> {
  const fromAsset = deps.fromAsset ?? 'USDC'
  return runPortalSwapLeg(swapId, snapshot, fromAsset, deps)
}

/** @deprecated Utiliser executeTrade — alias conservé 1 sprint. */
export const executeBundleTrade = executeTrade
export type ExecuteBundleTradeDeps = ExecuteTradeDeps
export type ExecuteBundleTradeResult = ExecuteTradeResult
