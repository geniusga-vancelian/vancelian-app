/**
 * Refresh LI.FI + slippage par leg bundle (phase 2 quote freshness).
 */
import type { BundleAllocationLeg, BundleRebalanceLeg, BundleWithdrawSellLeg } from '@/lib/portal/bundleClient'
import { confirmSwapWithRetry } from '@/lib/portal/swapQuoteConfirm'
import { SwapPriceChangedError, type SwapExecutePayload } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type BundleLegQuoteSnapshot = {
  review_estimated_receive: string
  review_amount_in: string
}

const BUNDLE_LEG_PRICE_RETRY_ON_CHANGED = 1

function fmtAmount(value: number | string | null | undefined): string | null {
  if (value == null) return null
  const n = typeof value === 'number' ? value : Number(String(value).replace(',', '.'))
  if (!Number.isFinite(n) || n < 0) return null
  return String(n)
}

export function snapshotFromInvestLeg(leg: BundleAllocationLeg): BundleLegQuoteSnapshot | null {
  const amountIn = fmtAmount(leg.entry_asset_consumed)
  const receive = fmtAmount(leg.crypto_received)
  if (!amountIn) return null
  return {
    review_amount_in: amountIn,
    review_estimated_receive: receive ?? '0',
  }
}

export function snapshotFromWithdrawLeg(leg: BundleWithdrawSellLeg): BundleLegQuoteSnapshot | null {
  const amountIn = fmtAmount(leg.quantity_sold)
  const receive = fmtAmount(leg.entry_asset_received)
  if (!amountIn) return null
  return {
    review_amount_in: amountIn,
    review_estimated_receive: receive ?? '0',
  }
}

export function snapshotFromRebalanceSellLeg(leg: {
  quantity_sold?: number
  entry_asset_received?: number
}): BundleLegQuoteSnapshot | null {
  const amountIn = fmtAmount(leg.quantity_sold)
  const receive = fmtAmount(leg.entry_asset_received)
  if (!amountIn) return null
  return {
    review_amount_in: amountIn,
    review_estimated_receive: receive ?? '0',
  }
}

export function snapshotFromRebalanceBuyLeg(leg: {
  entry_asset_spent?: number
  quantity_bought?: number
}): BundleLegQuoteSnapshot | null {
  const amountIn = fmtAmount(leg.entry_asset_spent)
  const receive = fmtAmount(leg.quantity_bought)
  if (!amountIn) return null
  return {
    review_amount_in: amountIn,
    review_estimated_receive: receive ?? '0',
  }
}

export function snapshotFromRebalanceLeg(leg: BundleRebalanceLeg, side: 'buy' | 'sell'): BundleLegQuoteSnapshot | null {
  const row = leg as BundleRebalanceLeg & {
    quantity_sold?: number
    entry_asset_received?: number
    entry_asset_spent?: number
    quantity_bought?: number
  }
  return side === 'sell' ? snapshotFromRebalanceSellLeg(row) : snapshotFromRebalanceBuyLeg(row)
}

async function confirmOnce(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
): Promise<SwapExecutePayload> {
  const confirmed = await confirmSwapWithRetry({
    swap_id: swapId,
    review_estimated_receive: snapshot.review_estimated_receive,
    review_amount_in: snapshot.review_amount_in,
  })
  return confirmed.execute
}

/**
 * Refresh quote LI.FI, vérifie le slippage vs snapshot leg, retourne le payload signable.
 */
export async function bundleLegConfirmAndPrepare(
  swapId: string,
  snapshot: BundleLegQuoteSnapshot,
  deps?: { onPhaseChange?: (phase: SwapExecutionPhase) => void },
): Promise<SwapExecutePayload> {
  deps?.onPhaseChange?.('verifying_price')
  let lastPriceChange: SwapPriceChangedError | undefined
  let current = snapshot

  for (let attempt = 0; attempt <= BUNDLE_LEG_PRICE_RETRY_ON_CHANGED; attempt += 1) {
    try {
      const exec = await confirmOnce(swapId, current)
      deps?.onPhaseChange?.('preparing')
      return exec
    } catch (err) {
      if (err instanceof SwapPriceChangedError) {
        lastPriceChange = err
        current = {
          review_amount_in: err.freshQuote.amount_in,
          review_estimated_receive: err.freshQuote.estimated_receive,
        }
        continue
      }
      throw err
    }
  }

  throw (
    lastPriceChange ??
    new Error('Le prix a trop bougé pour ce leg — réessayez dans quelques instants.')
  )
}
