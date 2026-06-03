'use client'

import { useCallback, useRef } from 'react'

import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import {
  bundleLegPrepareSign,
  fetchActiveBundleInvestLock,
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
  BundleLegSkippableError,
  isInfraOrchestrationError,
  legSkippableFromUnknown,
  mergeLegOutcomesIntoInvest,
  resolveTerminalStatusFromOutcomes,
  type BundleInvestTerminalStatus,
  type BundleLegOutcome,
} from '@/lib/portal/bundleInvestOrchestration'
import {
  BUNDLE_MAX_LEG_AUTO_RETRIES,
  BundleInvestTerminalError,
  buildBundleInvestTechnicalDetails,
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
  terminalStatus: BundleInvestTerminalStatus
  legOutcomes: BundleLegOutcome[]
  backendLockPending?: boolean
}

async function tryExecuteSingleLeg(
  invest: BundleInvestPayload,
  leg: NonNullable<BundleInvestPayload['allocation_details']>[number],
  deps: {
    signAndSubmit: ReturnType<typeof useLifiSwapExecution>['signAndSubmit']
    onPhaseChange?: (phase: SwapExecutionPhase) => void
  },
): Promise<{ entryDelta: number; txHash?: string | null }> {
  const swapId = leg.swap_id!
  const mapped = mapBundleSigningToExecute(leg.signing, swapId)
  const exec = mapped ?? (await bundleLegPrepareSign(swapId))
  deps.onPhaseChange?.('signing')
  await deps.signAndSubmit(exec)
  deps.onPhaseChange?.('submitting')
  const terminal = await pollBundleLegUntilTerminal(swapId, { invest, asset: leg.asset })
  return {
    entryDelta: Number(leg.entry_asset_consumed ?? 0),
    txHash: terminal.tx_hash ?? null,
  }
}

/**
 * Backend `finalize_lifi_batch` accepte un `entry_consumed` partiel et appelle `clear_invest_lock`.
 * Limite documentée : legs encore en AWAITING_SIGNATURE en base peuvent subsister ; le lock
 * devrait être libéré après finalize réussi (sinon `backendLockPending` côté UI).
 */
async function executePendingLegs(
  invest: BundleInvestPayload,
  deps: {
    signAndSubmit: ReturnType<typeof useLifiSwapExecution>['signAndSubmit']
    onLegProgress?: (current: number, total: number, asset: string) => void
    onPhaseChange?: (phase: SwapExecutionPhase) => void
  },
): Promise<{
  invest: BundleInvestPayload
  finalize?: BundleFinalizePayload
  terminalStatus: BundleInvestTerminalStatus
  legOutcomes: BundleLegOutcome[]
  backendLockPending?: boolean
}> {
  const pending = pendingBundleLegs(invest)
  const legOutcomes: BundleLegOutcome[] = []
  let entryConsumed = Number(invest.total_entry_asset_consumed ?? 0)

  if (pending.length > 0 && !invest.entry_instrument_id) {
    throw new Error('entry_instrument_id manquant — rechargez la page et réessayez.')
  }

  const total = pending.length
  for (let i = 0; i < pending.length; i += 1) {
    const leg = pending[i]!
    const swapId = leg.swap_id!
    deps.onLegProgress?.(i + 1, total, leg.asset)

    let attempts = 0
    let confirmed = false
    let lastSkippable: BundleLegSkippableError | undefined

    while (attempts <= BUNDLE_MAX_LEG_AUTO_RETRIES) {
      try {
        const { entryDelta, txHash } = await tryExecuteSingleLeg(invest, leg, deps)
        entryConsumed += entryDelta
        legOutcomes.push({
          asset: leg.asset,
          swapId,
          status: 'confirmed',
          attempts: attempts + 1,
          amountUsdc: Number(leg.entry_asset_consumed ?? 0),
          txHash,
        })
        confirmed = true
        break
      } catch (err) {
        if (err instanceof BundleInvestTerminalError) throw err
        if (isInfraOrchestrationError(err)) {
          throw new BundleInvestTerminalError({
            variant: 'reconciliation_required',
            message: err instanceof Error ? err.message : String(err),
            technicalDetails: buildBundleInvestTechnicalDetails({
              batchId: invest.batch_id,
              failedAsset: leg.asset,
              legStatus: leg.status,
            }),
          })
        }
        lastSkippable =
          err instanceof BundleLegSkippableError ? err : legSkippableFromUnknown(err)
        attempts += 1
      }
    }

    if (!confirmed) {
      legOutcomes.push({
        asset: leg.asset,
        swapId,
        status: 'skipped_failed',
        attempts: Math.max(attempts, 1),
        amountUsdc: Number(leg.entry_asset_consumed ?? 0),
        errorCategory: lastSkippable?.category ?? 'unknown',
      })
    }
  }

  let finalize: BundleFinalizePayload | undefined
  let finalizeError = false
  const shouldFinalize =
    Boolean(invest.entry_instrument_id) &&
    (Number(invest.total_entry_asset_received ?? 0) > 0 ||
      entryConsumed > 0 ||
      legOutcomes.some((o) => o.status === 'confirmed') ||
      legOutcomes.some((o) => o.status === 'skipped_failed'))

  if (shouldFinalize && invest.entry_instrument_id) {
    deps.onPhaseChange?.('bridging')
    try {
      finalize = await finalizeBundleBatch({
        portfolio_id: invest.portfolio_id,
        batch_id: invest.batch_id,
        entry_instrument_id: invest.entry_instrument_id,
        planned_entry_total: Number(invest.total_entry_asset_received ?? 0),
        entry_consumed: entryConsumed,
      })
      deps.onPhaseChange?.('completed')
    } catch (err) {
      finalizeError = true
      if (!isInfraOrchestrationError(err)) {
        throw err
      }
    }
  }

  const mergedInvest = mergeLegOutcomesIntoInvest(invest, legOutcomes)
  let terminalStatus = resolveTerminalStatusFromOutcomes(legOutcomes, mergedInvest, {
    finalize,
    finalizeError,
  })

  let backendLockPending = false
  if (!finalizeError && terminalStatus !== 'failed_no_allocation') {
    try {
      const active = await fetchActiveBundleInvestLock(invest.portfolio_id)
      backendLockPending =
        active.status === 'active' &&
        active.lock?.batch_id === invest.batch_id
    } catch {
      backendLockPending = false
    }
  }

  return {
    invest: mergedInvest,
    finalize,
    terminalStatus,
    legOutcomes,
    backendLockPending: backendLockPending || undefined,
  }
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

      const pending = pendingBundleLegs(invest)
      if (pending.length === 0) {
        const terminalStatus = resolveTerminalStatusFromOutcomes([], invest)
        clearBundleInvestSession(invest.portfolio_id)
        return { invest, terminalStatus, legOutcomes: [] }
      }

      const outcome = await executePendingLegs(invest, {
        signAndSubmit,
        onLegProgress,
        onPhaseChange,
      })

      clearBundleInvestSession(invest.portfolio_id)
      return {
        invest: outcome.invest,
        finalize: outcome.finalize,
        terminalStatus: outcome.terminalStatus,
        legOutcomes: outcome.legOutcomes,
        backendLockPending: outcome.backendLockPending,
      }
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
          const terminalStatus = resolveTerminalStatusFromOutcomes([], invest)
          return { invest, terminalStatus, legOutcomes: [] }
        }

        return await runFromInvestPayload(invest, {
          portfolioId: body.portfolio_id,
          fundingAsset: body.funding_asset,
          fundingAmount: body.funding_amount,
        })
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
