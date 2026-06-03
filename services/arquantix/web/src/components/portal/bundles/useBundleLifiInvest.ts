'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  bundleLegPrepareSign,
  finalizeBundleBatch,
  investBundle,
  mapBundleSigningToExecute,
  pendingBundleLegs,
  submitBundleLegTx,
  type BundleFinalizePayload,
  type BundleInvestPayload,
  type BundleInvestResult,
} from '@/lib/portal/bundleClient'
import {
  BUNDLE_MAX_LEG_AUTO_RETRIES,
  BundleInvestTerminalError,
  buildBundleInvestTechnicalDetails,
  detectPartialBundleSuccess,
  pollBundleLegUntilTerminal,
} from '@/lib/portal/bundleInvestTerminalization'
import {
  clearBundleInvestSession,
  saveBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type BundleInvestRunResult = {
  invest: BundleInvestPayload
  finalize?: BundleFinalizePayload
}

async function executePendingLegs(
  invest: BundleInvestPayload,
  deps: {
    signAndSubmit: ReturnType<typeof useLifiSwapExecution>['signAndSubmit']
    onLegProgress?: (current: number, total: number, asset: string) => void
    onPhaseChange?: (phase: SwapExecutionPhase) => void
  },
): Promise<{ entryConsumed: number; finalize?: BundleFinalizePayload }> {
  const pending = pendingBundleLegs(invest)
  if (pending.length === 0) {
    return { entryConsumed: Number(invest.total_entry_asset_consumed ?? 0) }
  }

  if (!invest.entry_instrument_id) {
    throw new Error('entry_instrument_id manquant — rechargez la page et réessayez.')
  }

  let entryConsumed = Number(invest.total_entry_asset_consumed ?? 0)
  const total = pending.length

  for (let i = 0; i < pending.length; i += 1) {
    const leg = pending[i]!
    const swapId = leg.swap_id!
    deps.onLegProgress?.(i + 1, total, leg.asset)

    let attempts = 0
    let lastError: unknown
    while (attempts <= BUNDLE_MAX_LEG_AUTO_RETRIES) {
      try {
        const mapped = mapBundleSigningToExecute(leg.signing, swapId)
        const exec = mapped ?? (await bundleLegPrepareSign(swapId))
        deps.onPhaseChange?.('signing')
        await deps.signAndSubmit(exec)
        deps.onPhaseChange?.('submitting')
        await pollBundleLegUntilTerminal(swapId, { invest, asset: leg.asset })
        entryConsumed += Number(leg.entry_asset_consumed ?? 0)
        lastError = null
        break
      } catch (err) {
        lastError = err
        if (err instanceof BundleInvestTerminalError) throw err
        attempts += 1
        if (attempts > BUNDLE_MAX_LEG_AUTO_RETRIES) {
          const variant = detectPartialBundleSuccess(invest)
            ? 'reconciliation_required'
            : 'impossible'
          throw new BundleInvestTerminalError({
            variant,
            message: err instanceof Error ? err.message : String(err),
            technicalDetails: buildBundleInvestTechnicalDetails({
              batchId: invest.batch_id,
              failedAsset: leg.asset,
              legStatus: leg.status,
            }),
          })
        }
      }
    }

    if (lastError) {
      throw lastError
    }
  }

  deps.onPhaseChange?.('bridging')
  const finalize = await finalizeBundleBatch({
    portfolio_id: invest.portfolio_id,
    batch_id: invest.batch_id,
    entry_instrument_id: invest.entry_instrument_id,
    planned_entry_total: Number(invest.total_entry_asset_received ?? 0),
    entry_consumed: entryConsumed,
  })

  deps.onPhaseChange?.('completed')
  return { entryConsumed, finalize }
}

export function useBundleLifiInvest(
  swapMockMode = false,
  entryAsset?: string,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  onLegProgress?: (current: number, total: number, asset: string) => void,
) {
  const inFlightRef = useRef(false)
  const { signAndSubmit } = useLifiSwapExecution(
    swapMockMode,
    onPhaseChange,
    entryAsset,
    { submitTx: submitBundleLegTx },
  )

  const runFromInvestPayload = useCallback(
    async (
      invest: BundleInvestPayload,
      sessionMeta?: Pick<BundleInvestSession, 'portfolioId' | 'fundingAsset' | 'fundingAmount'>,
    ): Promise<BundleInvestRunResult> => {
      if (sessionMeta) {
        saveBundleInvestSession({
          portfolioId: sessionMeta.portfolioId,
          batchId: invest.batch_id,
          fundingAsset: sessionMeta.fundingAsset,
          fundingAmount: sessionMeta.fundingAmount,
          invest,
          savedAt: new Date().toISOString(),
        })
      }

      const { finalize } = await executePendingLegs(invest, {
        signAndSubmit,
        onLegProgress,
        onPhaseChange,
      })

      clearBundleInvestSession(invest.portfolio_id)
      return { invest, finalize }
    },
    [onLegProgress, onPhaseChange, signAndSubmit],
  )

  const runInvest = useCallback(
    async (body: {
      portfolio_id: string
      funding_asset: string
      funding_amount: number
    }): Promise<BundleInvestResult | BundleInvestRunResult> => {
      if (inFlightRef.current) {
        throw new Error('Un investissement est déjà en cours sur cet appareil.')
      }
      inFlightRef.current = true
      try {
        const outcome = await investBundle(body)
        if (outcome.kind === 'already_pending') {
          return outcome
        }

        const invest = outcome.payload
        const pending = pendingBundleLegs(invest)
        if (pending.length === 0) {
          clearBundleInvestSession(body.portfolio_id)
          return { invest }
        }

        const result = await runFromInvestPayload(invest, {
          portfolioId: body.portfolio_id,
          fundingAsset: body.funding_asset,
          fundingAmount: body.funding_amount,
        })
        return result
      } finally {
        inFlightRef.current = false
      }
    },
    [runFromInvestPayload],
  )

  const resumeSession = useCallback(
    async (session: BundleInvestSession): Promise<BundleInvestRunResult> => {
      if (inFlightRef.current) {
        throw new Error('Reprise déjà en cours.')
      }
      inFlightRef.current = true
      try {
        return await runFromInvestPayload(session.invest, {
          portfolioId: session.portfolioId,
          fundingAsset: session.fundingAsset,
          fundingAmount: session.fundingAmount,
        })
      } finally {
        inFlightRef.current = false
      }
    },
    [runFromInvestPayload],
  )

  return { runInvest, resumeSession, inFlightRef }
}
