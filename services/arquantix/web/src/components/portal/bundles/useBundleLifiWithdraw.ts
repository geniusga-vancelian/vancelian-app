'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  finalizeBundleWithdraw,
  pendingWithdrawLegs,
  submitBundleLegTx,
  withdrawBundle,
  type BundleWithdrawFinalizePayload,
  type BundleWithdrawPayload,
  type BundleWithdrawResult,
} from '@/lib/portal/bundleClient'
import {
  clearBundleWithdrawSession,
  saveBundleWithdrawSession,
  type BundleWithdrawSession,
} from '@/lib/portal/bundleWithdrawSession'
import type { BundleWithdrawProcessingProgress } from '@/components/portal/transaction/mappers/bundleSteps'
import {
  bundleLegConfirmAndPrepare,
  snapshotFromWithdrawLeg,
} from '@/lib/portal/bundleLegQuoteConfirm'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type BundleWithdrawRunResult = {
  withdraw: BundleWithdrawPayload
  finalize?: BundleWithdrawFinalizePayload
}

async function executePendingSellLegs(
  withdraw: BundleWithdrawPayload,
  deps: {
    signAndSubmit: ReturnType<typeof useLifiSwapExecution>['signAndSubmit']
    pollUntilTerminal: ReturnType<typeof useLifiSwapExecution>['pollUntilTerminal']
    onLegProgress?: (current: number, total: number, asset: string) => void
    onPhaseChange?: (phase: SwapExecutionPhase) => void
    onProcessingProgress?: (progress: BundleWithdrawProcessingProgress) => void
  },
): Promise<{ finalize?: BundleWithdrawFinalizePayload }> {
  const pending = pendingWithdrawLegs(withdraw)
  const entryAsset = withdraw.entry_asset ?? 'USDC'
  const unwindAssets = pending.map((leg) => leg.asset)

  if (pending.length === 0) {
    if (withdraw.release?.released) {
      return {}
    }
    deps.onProcessingProgress?.({
      stage: 'transferring',
      entryAsset,
      unwindAssets: [],
      unwindLegTotal: 0,
    })
    deps.onPhaseChange?.('bridging')
    const finalize = await finalizeBundleWithdraw({
      portfolio_id: withdraw.portfolio_id,
      batch_id: withdraw.batch_id,
    })
    deps.onPhaseChange?.('completed')
    deps.onProcessingProgress?.({
      stage: 'completed',
      entryAsset,
      unwindAssets: [],
      unwindLegTotal: 0,
    })
    return { finalize }
  }

  const total = pending.length
  for (let i = 0; i < pending.length; i += 1) {
    const leg = pending[i]!
    const swapId = leg.swap_id!
    deps.onLegProgress?.(i + 1, total, leg.asset)
    deps.onProcessingProgress?.({
      stage: 'deallocating',
      entryAsset,
      unwindAssets,
      unwindLegCurrent: i + 1,
      unwindLegTotal: total,
      activeAsset: leg.asset,
    })

    const snapshot = snapshotFromWithdrawLeg(leg)
    if (!snapshot) {
      throw new Error(`Estimation manquante pour ${leg.asset} — rechargez et réessayez.`)
    }
    const exec = await bundleLegConfirmAndPrepare(swapId, snapshot, deps)
    deps.onPhaseChange?.('signing')
    await deps.signAndSubmit(exec)
    deps.onPhaseChange?.('submitting')
    await deps.pollUntilTerminal(swapId)
  }

  deps.onProcessingProgress?.({
    stage: 'transferring',
    entryAsset,
    unwindAssets,
    unwindLegTotal: total,
  })
  deps.onPhaseChange?.('bridging')
  const finalize = await finalizeBundleWithdraw({
    portfolio_id: withdraw.portfolio_id,
    batch_id: withdraw.batch_id,
  })
  deps.onPhaseChange?.('completed')
  deps.onProcessingProgress?.({
    stage: 'completed',
    entryAsset,
    unwindAssets,
    unwindLegTotal: total,
  })
  return { finalize }
}

export function useBundleLifiWithdraw(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onLegProgress?: (current: number, total: number, asset: string) => void,
  onProcessingProgress?: (progress: BundleWithdrawProcessingProgress) => void,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    { submitTx: submitBundleLegTx },
  )

  const runFromWithdrawPayload = useCallback(
    async (
      withdraw: BundleWithdrawPayload,
      sessionMeta?: Pick<
        BundleWithdrawSession,
        'portfolioId' | 'fullWithdraw' | 'withdrawAmount'
      >,
    ): Promise<BundleWithdrawRunResult> => {
      if (sessionMeta) {
        saveBundleWithdrawSession({
          portfolioId: sessionMeta.portfolioId,
          batchId: withdraw.batch_id,
          fullWithdraw: sessionMeta.fullWithdraw,
          withdrawAmount: sessionMeta.withdrawAmount,
          withdraw,
          savedAt: new Date().toISOString(),
        })
      }

      const { finalize } = await executePendingSellLegs(withdraw, {
        signAndSubmit,
        pollUntilTerminal,
        onLegProgress,
        onPhaseChange,
        onProcessingProgress,
      })

      clearBundleWithdrawSession(withdraw.portfolio_id)
      return { withdraw, finalize }
    },
    [onLegProgress, onPhaseChange, onProcessingProgress, pollUntilTerminal, signAndSubmit],
  )

  const runWithdraw = useCallback(
    async (body: {
      portfolio_id: string
      withdraw_amount?: number
      full_withdraw?: boolean
    }): Promise<BundleWithdrawResult | BundleWithdrawRunResult> => {
      if (inFlightRef.current) {
        throw new Error('Un retrait est déjà en cours sur cet appareil.')
      }
      inFlightRef.current = true
      try {
        onProcessingProgress?.({ stage: 'preparing' })
        const outcome = await withdrawBundle(body)
        if (outcome.kind === 'already_pending') {
          return outcome
        }

        const withdraw = outcome.payload
        if (withdraw.status === 'released' && withdraw.release?.released) {
          clearBundleWithdrawSession(body.portfolio_id)
          return { withdraw }
        }

        const pending = pendingWithdrawLegs(withdraw)
        if (pending.length === 0 && withdraw.status !== 'ready_to_release') {
          clearBundleWithdrawSession(body.portfolio_id)
          return { withdraw }
        }

        const result = await runFromWithdrawPayload(withdraw, {
          portfolioId: body.portfolio_id,
          fullWithdraw: Boolean(body.full_withdraw),
          withdrawAmount: body.full_withdraw ? null : (body.withdraw_amount ?? null),
        })
        return result
      } finally {
        inFlightRef.current = false
      }
    },
    [onProcessingProgress, runFromWithdrawPayload],
  )

  const resumeSession = useCallback(
    async (session: BundleWithdrawSession): Promise<BundleWithdrawRunResult> => {
      if (inFlightRef.current) {
        throw new Error('Reprise déjà en cours.')
      }
      inFlightRef.current = true
      try {
        onProcessingProgress?.({ stage: 'preparing' })
        return await runFromWithdrawPayload(session.withdraw, {
          portfolioId: session.portfolioId,
          fullWithdraw: session.fullWithdraw,
          withdrawAmount: session.withdrawAmount,
        })
      } finally {
        inFlightRef.current = false
      }
    },
    [onProcessingProgress, runFromWithdrawPayload],
  )

  return { runWithdraw, resumeSession, inFlightRef }
}
