import type { ExecuteTradeDeps } from '@/lib/portal/executeTrade'
import {
  fetchActiveBundleOperation,
  resumePortfolioRebalancing,
  type BundleActiveOperationPayload,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { runSequentialTrades } from '@/lib/portal/tradeChainRunner'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

const V3_DEPOSIT_POLL_MS = 2000
const V3_DEPOSIT_POLL_MAX_ATTEMPTS = 45

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

/** Dépôt V3 : seul COMPLETED (ou FAILED) clôt la session — pas residual après leg 1. */
function isDepositInvestTerminal(status: string | undefined | null): boolean {
  return status === 'COMPLETED' || status === 'FAILED'
}

async function resumeDepositChain(params: {
  portfolioId: string
  initial: PortfolioRebalancingPayload
  signAndSubmit: ExecuteTradeDeps['signAndSubmit']
  pollUntilTerminal: ExecuteTradeDeps['pollUntilTerminal']
  onPhaseChange?: (phase: SwapExecutionPhase) => void
  onAssetLines?: (lines: PortfolioRebalancingAssetLine[]) => void
}): Promise<PortfolioRebalancingPayload> {
  return resumeActiveBundleOperation(params)
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
  signAndSubmit: ExecuteTradeDeps['signAndSubmit']
  pollUntilTerminal: ExecuteTradeDeps['pollUntilTerminal']
  onPhaseChange?: (phase: SwapExecutionPhase) => void
  onAssetLines?: (lines: PortfolioRebalancingAssetLine[]) => void
}): Promise<PortfolioRebalancingPayload | null> {
  for (let attempt = 0; attempt < V3_DEPOSIT_POLL_MAX_ATTEMPTS; attempt += 1) {
    const active = await fetchActiveBundleOperation(params.portfolioId)
    if (active.status === 'none') {
      return null
    }
    if (isDepositInvestTerminal(active.v3_status)) {
      return toResumePayload(active)
    }
    if (hasSignablePendingLegs(active)) {
      const initial = toResumePayload(active)
      if (!initial) {
        await sleep(V3_DEPOSIT_POLL_MS)
        continue
      }
      return resumeDepositChain({
        portfolioId: params.portfolioId,
        initial,
        signAndSubmit: params.signAndSubmit,
        pollUntilTerminal: params.pollUntilTerminal,
        onPhaseChange: params.onPhaseChange,
        onAssetLines: params.onAssetLines,
      })
    }
    if (active.v3_status === 'RUNNING') {
      const progressed = await resumePortfolioRebalancing(params.portfolioId)
      if (isDepositInvestTerminal(progressed.v3_status)) {
        return progressed
      }
      if (hasSignablePendingLegs(progressed)) {
        return resumeDepositChain({
          portfolioId: params.portfolioId,
          initial: progressed,
          signAndSubmit: params.signAndSubmit,
          pollUntilTerminal: params.pollUntilTerminal,
          onPhaseChange: params.onPhaseChange,
          onAssetLines: params.onAssetLines,
        })
      }
      if (
        progressed.v3_status === 'COMPLETED_WITH_RESIDUAL_CASH' ||
        progressed.v3_status === 'RUNNING'
      ) {
        const retry = await resumePortfolioRebalancing(params.portfolioId)
        if (hasSignablePendingLegs(retry)) {
          return resumeDepositChain({
            portfolioId: params.portfolioId,
            initial: retry,
            signAndSubmit: params.signAndSubmit,
            pollUntilTerminal: params.pollUntilTerminal,
            onPhaseChange: params.onPhaseChange,
            onAssetLines: params.onAssetLines,
          })
        }
        if (isDepositInvestTerminal(retry.v3_status)) {
          return retry
        }
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
  signAndSubmit: ExecuteTradeDeps['signAndSubmit']
  pollUntilTerminal: ExecuteTradeDeps['pollUntilTerminal']
  onPhaseChange?: (phase: SwapExecutionPhase) => void
  onAssetLines?: (lines: PortfolioRebalancingAssetLine[]) => void
}): Promise<PortfolioRebalancingPayload> {
  const { payload: result, lastResumeError } = await runSequentialTrades({
    initial: params.initial,
    tradeDeps: {
      signAndSubmit: params.signAndSubmit,
      pollUntilTerminal: params.pollUntilTerminal,
      onPhaseChange: params.onPhaseChange,
    },
    resumeFn: resumePortfolioRebalancing,
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
  if (lastResumeError) {
    throw new Error(lastResumeError)
  }
  return result
}
