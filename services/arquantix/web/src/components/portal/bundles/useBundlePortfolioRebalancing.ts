'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  executePortfolioRebalancing,
  submitBundleLegTx,
  type BundleRebalanceLeg,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { bundleLegConfirmAndPrepare } from '@/lib/portal/bundleLegQuoteConfirm'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type PendingLeg = BundleRebalanceLeg & { side: 'buy' | 'sell' }

function v3Snapshot(leg: PendingLeg) {
  const amount = String(
    (leg as BundleRebalanceLeg & { amount_usdc?: string }).amount_usdc ??
      (leg.side === 'sell' ? leg.quantity_sold : leg.entry_asset_spent) ??
      '0',
  )
  return {
    review_amount_in: amount,
    review_estimated_receive: '0',
  }
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

export function assetLineLabel(line: PortfolioRebalancingAssetLine): string {
  const action = line.action === 'sell' ? 'Vente' : 'Achat'
  const status =
    line.status === 'completed'
      ? 'Terminé'
      : line.status === 'pending'
        ? 'Signature en cours…'
        : line.status === 'failed'
          ? 'Échec'
          : line.status === 'planned'
            ? 'Planifié'
            : line.status
  return `${line.asset} — ${action} — ${status}`
}

export function useBundlePortfolioRebalancing(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onAssetStatus?: (asset: string, status: string) => void,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    { submitTx: submitBundleLegTx },
  )

  const runPortfolioRebalancing = useCallback(
    async (portfolioId: string): Promise<PortfolioRebalancingPayload> => {
      if (inFlightRef.current) {
        throw new Error('Un rééquilibrage est déjà en cours.')
      }
      inFlightRef.current = true
      try {
        onPhaseChange?.('preparing')
        const result = await executePortfolioRebalancing(portfolioId)
        for (const line of result.asset_lines ?? []) {
          onAssetStatus?.(line.asset, line.status)
        }

        const pending = pendingLegs(result)
        for (const leg of pending) {
          onAssetStatus?.(leg.asset, 'signing')
          const swapId = leg.swap_id!
          const exec = await bundleLegConfirmAndPrepare(swapId, v3Snapshot(leg), {
            onPhaseChange,
          })
          onPhaseChange?.('signing')
          await signAndSubmit(exec)
          onPhaseChange?.('submitting')
          await pollUntilTerminal(swapId)
          onAssetStatus?.(leg.asset, 'completed')
        }
        onPhaseChange?.('completed')
        return result
      } finally {
        inFlightRef.current = false
      }
    },
    [onAssetStatus, onPhaseChange, pollUntilTerminal, signAndSubmit],
  )

  return { runPortfolioRebalancing, inFlightRef }
}
