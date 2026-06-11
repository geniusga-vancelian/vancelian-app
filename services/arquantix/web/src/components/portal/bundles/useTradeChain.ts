'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import { submitSwapTx } from '@/lib/portal/swapClient'
import type { PortfolioRebalancingPayload } from '@/lib/portal/bundleClient'
import { runSequentialTrades, type RunSequentialTradesResult } from '@/lib/portal/tradeChainRunner'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export function useTradeChain(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onAssetStatus?: (asset: string, status: string) => void,
  onLegProgress?: (current: number, total: number, asset: string) => void,
  resumeFn?: (portfolioId: string) => Promise<PortfolioRebalancingPayload>,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    {
      submitTx: (swapId, txHash, walletAddress) =>
        submitSwapTx(swapId, txHash, walletAddress),
    },
  )

  const runChainedTrades = useCallback(
    async (initial: PortfolioRebalancingPayload): Promise<RunSequentialTradesResult> => {
      return runSequentialTrades({
        initial,
        tradeDeps: {
          signAndSubmit,
          pollUntilTerminal,
          onPhaseChange,
        },
        onAssetStatus,
        onLegProgress,
        resumeFn,
      })
    },
    [onAssetStatus, onLegProgress, onPhaseChange, pollUntilTerminal, resumeFn, signAndSubmit],
  )

  return { runChainedTrades, inFlightRef, signAndSubmit, pollUntilTerminal }
}
