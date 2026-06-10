import {
  executeBundleTrade,
  type ExecuteBundleTradeDeps,
} from '@/lib/portal/executeBundleTrade'
import {
  fetchActiveBundleOperation,
  resumePortfolioRebalancing,
  type BundleActiveOperationPayload,
  type BundleRebalanceLeg,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { isTerminalBundleV3Status } from '@/components/portal/transaction/mappers/bundleSteps'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

const V3_DEPOSIT_POLL_MS = 2000
const V3_DEPOSIT_POLL_MAX_ATTEMPTS = 45

type PendingLeg = BundleRebalanceLeg & { side: 'buy' | 'sell' }

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
  deps: ExecuteBundleTradeDeps & {
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

function hasSignablePendingLegs(
  payload: PortfolioRebalancingPayload | BundleActiveOperationPayload | null,
): boolean {
  if (!payload) return false
  const legs = [...(payload.sell_results ?? []), ...(payload.buy_results ?? [])]
  return legs.some(
    (leg) =>
      leg.status === 'pending' &&
      Boolean(leg.swap_id) &&
      (leg.error === 'awaiting_client_signature' ||
        leg.error === 'awaiting_wallet_signature' ||
        leg.error === 'awaiting_confirmation'),
  )
}

function toResumePayload(
  active: BundleActiveOperationPayload,
): PortfolioRebalancingPayload | null {
  if (active.v3_status !== 'RUNNING' && !active.rebalance_execution_id) {
    return null
  }
  return {
    portfolio_id: active.portfolio_id,
    status: 'running',
    v3_status: active.v3_status ?? 'RUNNING',
    rebalance_execution_id: active.rebalance_execution_id,
    asset_lines: active.asset_lines,
    sell_results: active.sell_results,
    buy_results: active.buy_results,
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Attend l'opération V3 dépôt puis signe les legs LI.FI dans la même session web. */
export async function completeV3DepositRebalance(params: {
  portfolioId: string
  signAndSubmit: ExecuteBundleTradeDeps['signAndSubmit']
  pollUntilTerminal: ExecuteBundleTradeDeps['pollUntilTerminal']
  onPhaseChange?: (phase: SwapExecutionPhase) => void
  onAssetLines?: (lines: PortfolioRebalancingAssetLine[]) => void
}): Promise<PortfolioRebalancingPayload | null> {
  for (let attempt = 0; attempt < V3_DEPOSIT_POLL_MAX_ATTEMPTS; attempt += 1) {
    const active = await fetchActiveBundleOperation(params.portfolioId)
    if (active.status === 'none' || isTerminalBundleV3Status(active.v3_status)) {
      if (active.status === 'active' && isTerminalBundleV3Status(active.v3_status)) {
        return toResumePayload(active)
      }
      return null
    }
    if (hasSignablePendingLegs(active)) {
      const initial = toResumePayload(active)
      if (!initial) {
        await sleep(V3_DEPOSIT_POLL_MS)
        continue
      }
      return resumeActiveBundleOperation({
        initial,
        signAndSubmit: params.signAndSubmit,
        pollUntilTerminal: params.pollUntilTerminal,
        onPhaseChange: params.onPhaseChange,
        onAssetLines: params.onAssetLines,
      })
    }
    if (active.v3_status === 'RUNNING') {
      const progressed = await resumePortfolioRebalancing(params.portfolioId)
      if (isTerminalBundleV3Status(progressed.v3_status)) {
        return progressed
      }
      if (hasSignablePendingLegs(progressed)) {
        return resumeActiveBundleOperation({
          initial: progressed,
          signAndSubmit: params.signAndSubmit,
          pollUntilTerminal: params.pollUntilTerminal,
          onPhaseChange: params.onPhaseChange,
          onAssetLines: params.onAssetLines,
        })
      }
    }
    await sleep(V3_DEPOSIT_POLL_MS)
  }
  throw new Error(
    'Le rééquilibrage automatique prend plus de temps que prévu — ouvrez le panier pour reprendre.',
  )
}

export async function resumeActiveBundleOperation(params: {
  initial: PortfolioRebalancingPayload
  signAndSubmit: ExecuteBundleTradeDeps['signAndSubmit']
  pollUntilTerminal: ExecuteBundleTradeDeps['pollUntilTerminal']
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
