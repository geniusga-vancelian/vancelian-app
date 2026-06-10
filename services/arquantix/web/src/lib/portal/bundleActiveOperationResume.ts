import { executeBundleTrade } from '@/lib/portal/executeBundleTrade'
import {
  resumePortfolioRebalancing,
  submitBundleLegTx,
  type BundleRebalanceLeg,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type PendingLeg = BundleRebalanceLeg & { side: 'buy' | 'sell' }

type SignDeps = {
  signAndSubmit: (
    swapId: string,
    snapshot: { review_amount_in: string; review_estimated_receive: string },
  ) => Promise<unknown>
  pollUntilTerminal: (swapId: string) => Promise<unknown>
}

function pendingLegs(result: PortfolioRebalancingPayload): PendingLeg[] {
  const sells = (result.sell_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'sell' as const }))
  const buys = (result.buy_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'buy' as const }))
  return [...sells, ...buys]
}

function v3Snapshot(leg: PendingLeg) {
  const amount = String(leg.amount_usdc ?? '0')
  return {
    review_amount_in: amount,
    review_estimated_receive: '0',
  }
}

async function runChainedTrades(
  initial: PortfolioRebalancingPayload,
  deps: {
    signAndSubmit: SignDeps['signAndSubmit']
    pollUntilTerminal: SignDeps['pollUntilTerminal']
    onPhaseChange?: (phase: SwapExecutionPhase) => void
    onAssetStatus?: (asset: string, status: string) => void
  },
): Promise<PortfolioRebalancingPayload> {
  let result = initial

  while (result.v3_status === 'RUNNING' || pendingLegs(result).length > 0) {
    const pending = pendingLegs(result)
    for (const leg of pending) {
      deps.onPhaseChange?.('signing')
      deps.onAssetStatus?.(leg.asset, 'signing')
      await executeBundleTrade(leg.swap_id!, v3Snapshot(leg), {
        signAndSubmit: deps.signAndSubmit,
        pollUntilTerminal: deps.pollUntilTerminal,
        onPhaseChange: deps.onPhaseChange,
      })
      deps.onAssetStatus?.(leg.asset, 'completed')
    }

    if (result.v3_status !== 'RUNNING') {
      break
    }

    result = await resumePortfolioRebalancing(result.portfolio_id)
    for (const line of result.asset_lines ?? []) {
      deps.onAssetStatus?.(line.asset, line.status)
    }
  }

  return result
}

export async function resumeActiveBundleOperation(params: {
  initial: PortfolioRebalancingPayload
  signAndSubmit: SignDeps['signAndSubmit']
  pollUntilTerminal: SignDeps['pollUntilTerminal']
  onPhaseChange?: (phase: SwapExecutionPhase) => void
  onAssetLines?: (lines: PortfolioRebalancingAssetLine[]) => void
}): Promise<PortfolioRebalancingPayload> {
  const result = await runChainedTrades(params.initial, {
    signAndSubmit: params.signAndSubmit,
    pollUntilTerminal: params.pollUntilTerminal,
    onPhaseChange: params.onPhaseChange,
    onAssetStatus: (asset, status) => {
      params.onAssetLines?.(
        (params.initial.asset_lines ?? []).map((line) =>
          line.asset === asset ? { ...line, status } : line,
        ),
      )
    },
  })
  if (result.asset_lines?.length) {
    params.onAssetLines?.(result.asset_lines)
  }
  return result
}
