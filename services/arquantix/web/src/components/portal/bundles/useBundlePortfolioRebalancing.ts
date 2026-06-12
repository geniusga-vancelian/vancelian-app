'use client'

import { useCallback } from 'react'

import { useTradeChain } from '@/components/portal/bundles/useTradeChain'
import {
  executePortfolioRebalancing,
  resumePortfolioRebalancing,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

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
        ? 'Préparation…'
        : line.status === 'signing' || line.status === 'approving'
          ? 'Signature en cours…'
          : line.status === 'submitting'
            ? 'Confirmation on-chain…'
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
  onReconcile?: (active: boolean, asset?: string) => void,
) {
  const { runChainedTrades, inFlightRef } = useTradeChain(
    swapMockMode,
    entryAsset,
    onPhaseChange,
    onAssetStatus,
    onLegProgress,
    resumePortfolioRebalancing,
    onReconcile,
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
        const chained = await runChainedTrades(initial)
        if (chained.lastResumeError) {
          throw new Error(chained.lastResumeError)
        }
        return chained.payload
      } finally {
        inFlightRef.current = false
      }
    },
    [inFlightRef, onAssetStatus, onPhaseChange, runChainedTrades],
  )

  return { runPortfolioRebalancing, inFlightRef }
}
