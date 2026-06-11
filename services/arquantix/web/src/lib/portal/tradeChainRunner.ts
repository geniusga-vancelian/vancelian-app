/**
 * Enchaîne des legs LI.FI comme des swaps simples successifs.
 * Un leg en échec n'arrête pas les suivants — même stratégie que bundle invest legacy.
 */
import { executeTrade, type ExecuteTradeDeps } from '@/lib/portal/executeTrade'
import { normalizeBundleResumeError } from '@/lib/portal/bundleResumeError'
import {
  snapshotFromRebalanceLeg,
  type BundleLegQuoteSnapshot,
} from '@/lib/portal/bundleLegQuoteConfirm'
import type { BundleRebalanceLeg, PortfolioRebalancingPayload } from '@/lib/portal/bundleClient'
import { isTerminalBundleV3Status } from '@/components/portal/transaction/mappers/bundleSteps'

const RESUME_RETRY_DELAY_MS = 800
const RESUME_MAX_ATTEMPTS = 2
const MAX_RESUME_ROUNDS = 12

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export type PendingRebalanceLeg = BundleRebalanceLeg & { side: 'buy' | 'sell' }

export type TradeLegOutcome = {
  asset: string
  swapId: string
  status: 'completed' | 'failed'
  errorMessage?: string
}

export function pendingRebalanceLegs(result: PortfolioRebalancingPayload): PendingRebalanceLeg[] {
  const sells = (result.sell_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'sell' as const }))
  const buys = (result.buy_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'buy' as const }))
  return [...sells, ...buys]
}

export function rebalanceLegSnapshot(leg: PendingRebalanceLeg): BundleLegQuoteSnapshot {
  const fromApi = snapshotFromRebalanceLeg(leg, leg.side)
  if (fromApi) {
    return fromApi
  }
  if (leg.amount_in && leg.estimated_receive) {
    return {
      review_amount_in: String(leg.amount_in),
      review_estimated_receive: String(leg.estimated_receive),
    }
  }
  throw new Error(
    `Montants LI.FI manquants pour ${leg.asset} — relancez le rééquilibrage.`,
  )
}

export function rebalanceLegFromAsset(leg: PendingRebalanceLeg, entryAsset = 'USDC'): string {
  if (leg.from_asset) {
    return leg.from_asset
  }
  return leg.side === 'sell' ? leg.asset : entryAsset
}

export type ExecuteLegFn = (
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps: ExecuteTradeDeps,
) => Promise<void>

export type RunSequentialTradesOptions = {
  initial: PortfolioRebalancingPayload
  tradeDeps: ExecuteTradeDeps
  entryAsset?: string
  executeLeg?: ExecuteLegFn
  snapshotForLeg?: (leg: PendingRebalanceLeg) => BundleLegQuoteSnapshot
  onAssetStatus?: (asset: string, status: string) => void
  onLegProgress?: (current: number, total: number, asset: string) => void
  resumeFn?: (portfolioId: string) => Promise<PortfolioRebalancingPayload>
}

export type ResumeOutcome = {
  status: 'ok' | 'failed'
  attempts: number
  errorMessage?: string
}

export type RunSequentialTradesResult = {
  payload: PortfolioRebalancingPayload
  legOutcomes: TradeLegOutcome[]
  resumeOutcomes: ResumeOutcome[]
  lastResumeError: string | null
}

async function resumeWithRetry(
  resumeFn: (portfolioId: string) => Promise<PortfolioRebalancingPayload>,
  portfolioId: string,
  fallback: PortfolioRebalancingPayload,
): Promise<{ payload: PortfolioRebalancingPayload; outcome: ResumeOutcome }> {
  let lastError: unknown
  for (let attempt = 1; attempt <= RESUME_MAX_ATTEMPTS; attempt += 1) {
    try {
      const payload = await resumeFn(portfolioId)
      return { payload, outcome: { status: 'ok', attempts: attempt } }
    } catch (err) {
      lastError = err
      if (attempt < RESUME_MAX_ATTEMPTS) {
        await sleep(RESUME_RETRY_DELAY_MS * attempt)
      }
    }
  }
  const errorMessage = normalizeBundleResumeError(lastError)
  return {
    payload: fallback,
    outcome: { status: 'failed', attempts: RESUME_MAX_ATTEMPTS, errorMessage },
  }
}

export async function runSequentialTrades(
  options: RunSequentialTradesOptions,
): Promise<RunSequentialTradesResult> {
  let result = options.initial
  const legOutcomes: TradeLegOutcome[] = []
  const resumeOutcomes: ResumeOutcome[] = []
  let lastResumeError: string | null = null
  let resumeRounds = 0
  const snapshotForLeg = options.snapshotForLeg ?? rebalanceLegSnapshot
  const executeLeg =
    options.executeLeg ??
    (async (swapId, snapshot, deps) => {
      await executeTrade(swapId, snapshot, deps)
    })

  const plannedLegTotal = Math.max(
    (result.sell_results?.length ?? 0) + (result.buy_results?.length ?? 0),
    (result.asset_lines?.length ?? 0),
    1,
  )
  let executedLegCount = 0

  while (true) {
    if (isTerminalBundleV3Status(result.v3_status)) {
      break
    }

    const pending = pendingRebalanceLegs(result)
    if (pending.length > 0) {
      // Un seul swap par tour : quote LI.FI + signature Privy indépendants (ADR 008).
      const leg = pending[0]!
      const swapId = leg.swap_id!
      executedLegCount += 1
      options.onLegProgress?.(executedLegCount, plannedLegTotal, leg.asset)
      options.onAssetStatus?.(leg.asset, 'pending')

      try {
        const fromAsset = rebalanceLegFromAsset(leg, options.entryAsset)
        await executeLeg(swapId, snapshotForLeg(leg), {
          ...options.tradeDeps,
          fromAsset,
          onPhaseChange: (phase) => {
            options.tradeDeps.onPhaseChange?.(phase)
            if (phase === 'signing' || phase === 'approving') {
              options.onAssetStatus?.(leg.asset, 'signing')
            } else if (phase === 'submitting') {
              options.onAssetStatus?.(leg.asset, 'submitting')
            } else if (phase === 'completed') {
              options.onAssetStatus?.(leg.asset, 'completed')
            }
          },
        })
        options.onAssetStatus?.(leg.asset, 'completed')
        legOutcomes.push({ asset: leg.asset, swapId, status: 'completed' })
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err)
        options.onAssetStatus?.(leg.asset, 'failed')
        legOutcomes.push({
          asset: leg.asset,
          swapId,
          status: 'failed',
          errorMessage,
        })
      }
    } else if (result.v3_status !== 'RUNNING') {
      break
    }

    if (!options.resumeFn) {
      break
    }
    if (resumeRounds >= MAX_RESUME_ROUNDS) {
      break
    }
    if (result.v3_status !== 'RUNNING' && pending.length === 0) {
      break
    }

    resumeRounds += 1
    const resumed = await resumeWithRetry(options.resumeFn, result.portfolio_id, result)
    resumeOutcomes.push(resumed.outcome)

    if (resumed.outcome.status === 'failed') {
      lastResumeError = resumed.outcome.errorMessage ?? null
      break
    }

    result = resumed.payload

    if (isTerminalBundleV3Status(result.v3_status)) {
      break
    }

    for (const line of result.asset_lines ?? []) {
      options.onAssetStatus?.(line.asset, line.status)
    }
  }

  return { payload: result, legOutcomes, resumeOutcomes, lastResumeError }
}
