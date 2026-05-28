'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  bundleLegPrepareSign,
  executeBundleRebalance,
  mapBundleSigningToExecute,
  submitBundleLegTx,
  type BundleRebalanceLeg,
  type BundleRebalancePayload,
} from '@/lib/portal/bundleClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

function pendingRebalanceLegs(result: BundleRebalancePayload): BundleRebalanceLeg[] {
  const buys = (result.buy_results ?? []).filter(
    (leg) => leg.status === 'pending' && Boolean(leg.swap_id),
  )
  const sells = (result.sell_results ?? []).filter(
    (leg) => leg.status === 'pending' && Boolean(leg.swap_id),
  )
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
          const mapped =
            mapBundleSigningToExecute(leg.signing, swapId) ??
            (await bundleLegPrepareSign(swapId))
          onPhaseChange?.('signing')
          await signAndSubmit(mapped)
          onPhaseChange?.('submitting')
          await pollUntilTerminal(swapId)
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
