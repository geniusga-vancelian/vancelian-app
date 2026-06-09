'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  executeBundleRebalance,
  submitBundleLegTx,
  type BundleRebalanceLeg,
  type BundleRebalancePayload,
} from '@/lib/portal/bundleClient'
import { snapshotFromRebalanceLeg } from '@/lib/portal/bundleLegQuoteConfirm'
import { executeBundleTrade } from '@/lib/portal/executeBundleTrade'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type PendingRebalanceLeg = BundleRebalanceLeg & {
  side: 'buy' | 'sell'
  quantity_sold?: number
  entry_asset_received?: number
  entry_asset_spent?: number
  quantity_bought?: number
}

function pendingRebalanceLegs(result: BundleRebalancePayload): PendingRebalanceLeg[] {
  const sells = (result.sell_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'sell' as const }))
  const buys = (result.buy_results ?? [])
    .filter((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
    .map((leg) => ({ ...leg, side: 'buy' as const }))
  return [...sells, ...buys]
}

export function useBundleLifiRebalance(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onLegProgress?: (current: number, total: number, asset: string) => void,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    { submitTx: submitBundleLegTx },
  )

  const runRebalance = useCallback(
    async (portfolioId: string): Promise<BundleRebalancePayload> => {
      if (inFlightRef.current) {
        throw new Error('Une réallocation est déjà en cours.')
      }
      inFlightRef.current = true
      try {
        const result = await executeBundleRebalance(portfolioId)
        const pending = pendingRebalanceLegs(result)
        const total = pending.length
        for (let i = 0; i < pending.length; i += 1) {
          const leg = pending[i]!
          const swapId = leg.swap_id!
          onLegProgress?.(i + 1, total, leg.asset)
          const snapshot = snapshotFromRebalanceLeg(leg, leg.side)
          if (!snapshot) {
            throw new Error(`Estimation manquante pour ${leg.asset} — rechargez et réessayez.`)
          }
          await executeBundleTrade(swapId, snapshot, {
            signAndSubmit,
            pollUntilTerminal,
            onPhaseChange,
          })
        }
        onPhaseChange?.('completed')
        return result
      } finally {
        inFlightRef.current = false
      }
    },
    [onLegProgress, onPhaseChange, pollUntilTerminal, signAndSubmit],
  )

  return { runRebalance, inFlightRef }
}
