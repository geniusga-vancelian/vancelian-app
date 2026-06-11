/**
 * Enchaîne des legs LI.FI comme des swaps simples successifs.
 * Un leg en échec n'arrête pas les suivants — même stratégie que bundle invest legacy.
 */
import { executeTrade, type ExecuteTradeDeps } from '@/lib/portal/executeTrade'
import type { BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import type { BundleRebalanceLeg, PortfolioRebalancingPayload } from '@/lib/portal/bundleClient'
import { isTerminalBundleV3Status } from '@/components/portal/transaction/mappers/bundleSteps'

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
  const amount = String(leg.amount_usdc ?? '0')
  const row = leg as BundleRebalanceLeg & {
    quantity_bought?: number
    entry_asset_spent?: number
    quantity_sold?: number
    entry_asset_received?: number
    amount_crypto?: number | string
  }
  const receive =
    leg.side === 'buy'
      ? String(row.quantity_bought ?? row.amount_crypto ?? '0')
      : String(row.entry_asset_received ?? row.amount_usdc ?? '0')
  return {
    review_amount_in: amount,
    review_estimated_receive: receive,
  }
}

export type ExecuteLegFn = (
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps: ExecuteTradeDeps,
) => Promise<void>

export type RunSequentialTradesOptions = {
  initial: PortfolioRebalancingPayload
  tradeDeps: ExecuteTradeDeps
  executeLeg?: ExecuteLegFn
  snapshotForLeg?: (leg: PendingRebalanceLeg) => BundleLegQuoteSnapshot
  onAssetStatus?: (asset: string, status: string) => void
  onLegProgress?: (current: number, total: number, asset: string) => void
  resumeFn?: (portfolioId: string) => Promise<PortfolioRebalancingPayload>
}

export type RunSequentialTradesResult = {
  payload: PortfolioRebalancingPayload
  legOutcomes: TradeLegOutcome[]
}

export async function runSequentialTrades(
  options: RunSequentialTradesOptions,
): Promise<RunSequentialTradesResult> {
  let result = options.initial
  const legOutcomes: TradeLegOutcome[] = []
  const snapshotForLeg = options.snapshotForLeg ?? rebalanceLegSnapshot
  const executeLeg =
    options.executeLeg ??
    (async (swapId, snapshot, deps) => {
      await executeTrade(swapId, snapshot, deps)
    })

  while (result.v3_status === 'RUNNING' || pendingRebalanceLegs(result).length > 0) {
    const pending = pendingRebalanceLegs(result)
    const total = pending.length

    for (let i = 0; i < pending.length; i += 1) {
      const leg = pending[i]!
      const swapId = leg.swap_id!
      options.onLegProgress?.(i + 1, total, leg.asset)
      options.onAssetStatus?.(leg.asset, 'pending')

      try {
        await executeLeg(swapId, snapshotForLeg(leg), {
          ...options.tradeDeps,
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
    }

    if (result.v3_status !== 'RUNNING') {
      break
    }

    if (!options.resumeFn) {
      break
    }

    try {
      result = await options.resumeFn(result.portfolio_id)
    } catch (err) {
      const msg = err instanceof Error ? err.message : ''
      if (
        /no_running_rebalance|no running rebalance/i.test(msg) &&
        pendingRebalanceLegs(result).length === 0
      ) {
        break
      }
      throw err
    }

    if (
      isTerminalBundleV3Status(result.v3_status) &&
      pendingRebalanceLegs(result).length === 0
    ) {
      break
    }

    for (const line of result.asset_lines ?? []) {
      options.onAssetStatus?.(line.asset, line.status)
    }
  }

  return { payload: result, legOutcomes }
}
