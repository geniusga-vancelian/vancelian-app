'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  executePortfolioRebalancing,
  resumePortfolioRebalancing,
  submitBundleLegTx,
  type BundleRebalanceLeg,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { executeBundleTrade } from '@/lib/portal/executeBundleTrade'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type PendingLeg = BundleRebalanceLeg & { side: 'buy' | 'sell' }

function v3Snapshot(leg: PendingLeg) {
  const amount = String(leg.amount_usdc ?? '0')
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

function formatUsdcAmount(value: string | undefined): string | null {
  if (!value) return null
  const n = Number(value)
  if (!Number.isFinite(n)) return null
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function formatCryptoQty(value: string | undefined): string | null {
  if (!value) return null
  const n = Number(value)
  if (!Number.isFinite(n)) return null
  if (n >= 1) {
    return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 4 }).format(n)
  }
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 8 }).format(n)
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
  const entryAsset = line.entry_asset ?? 'USDC'
  const execUsdc = formatUsdcAmount(line.amount_entry)
  const execCrypto = formatCryptoQty(line.amount_crypto)
  const targetUsdc = formatUsdcAmount(line.target_value_usdc)
  const currentUsdc = formatUsdcAmount(line.current_value_usdc)

  const execPart = execUsdc
    ? execCrypto
      ? `${execUsdc} ${entryAsset} (~${execCrypto} ${line.asset})`
      : `${execUsdc} ${entryAsset}`
    : null
  const targetPart =
    targetUsdc && currentUsdc
      ? `cible ${targetUsdc} ${entryAsset} (actuel ${currentUsdc})`
      : targetUsdc
        ? `cible ${targetUsdc} ${entryAsset}`
        : null

  const parts = [`${line.asset}`, action]
  if (execPart) parts.push(execPart)
  if (targetPart) parts.push(targetPart)
  parts.push(status)
  return parts.join(' — ')
}

export function useBundlePortfolioRebalancing(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onAssetStatus?: (asset: string, status: string) => void,
  onLegProgress?: (current: number, total: number, asset: string) => void,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    { submitTx: submitBundleLegTx },
  )

  const runChainedTrades = useCallback(
    async (initial: PortfolioRebalancingPayload): Promise<PortfolioRebalancingPayload> => {
      let result = initial
      const tradeDeps = {
        signAndSubmit,
        pollUntilTerminal,
        onPhaseChange,
      }

      while (result.v3_status === 'RUNNING' || pendingLegs(result).length > 0) {
        const pending = pendingLegs(result)
        const total = pending.length
        for (let i = 0; i < pending.length; i += 1) {
          const leg = pending[i]!
          onLegProgress?.(i + 1, total, leg.asset)
          onAssetStatus?.(leg.asset, 'signing')
          await executeBundleTrade(leg.swap_id!, v3Snapshot(leg), tradeDeps)
          onAssetStatus?.(leg.asset, 'completed')
        }

        if (result.v3_status !== 'RUNNING') {
          break
        }

        result = await resumePortfolioRebalancing(result.portfolio_id)
        for (const line of result.asset_lines ?? []) {
          onAssetStatus?.(line.asset, line.status)
        }
      }

      return result
    },
    [onAssetStatus, onLegProgress, onPhaseChange, pollUntilTerminal, signAndSubmit],
  )

  const runPortfolioRebalancing = useCallback(
    async (portfolioId: string): Promise<PortfolioRebalancingPayload> => {
      if (inFlightRef.current) {
        throw new Error('Un rééquilibrage est déjà en cours.')
      }
      inFlightRef.current = true
      try {
        onPhaseChange?.('preparing')
        const initial = await executePortfolioRebalancing(portfolioId)
        for (const line of initial.asset_lines ?? []) {
          onAssetStatus?.(line.asset, line.status)
        }
        return await runChainedTrades(initial)
      } finally {
        inFlightRef.current = false
      }
    },
    [onAssetStatus, onPhaseChange, runChainedTrades],
  )

  return { runPortfolioRebalancing, inFlightRef }
}
