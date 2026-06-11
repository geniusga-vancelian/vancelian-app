'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import {
  assetLineLabel,
  useBundlePortfolioRebalancing,
} from '@/components/portal/bundles/useBundlePortfolioRebalancing'
import { AppButton } from '@/components/design-system/app/AppButton'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import {
  buildBundleRebalancingProcessingStepsDynamic,
  buildBundleRebalancingStepStates,
  isTerminalBundleV3Status,
  type BundleRebalancingProcessingProgress,
} from '@/components/portal/transaction/mappers/bundleSteps'
import { BUNDLE_FLOW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import {
  previewPortfolioRebalancing,
  reconcileStaleBundlePortfolioState,
  type BundleInvestActiveLockPayload,
  type PortfolioRebalancingAssetLine,
} from '@/lib/portal/bundleClient'
import { normalizeBundleResumeError } from '@/lib/portal/bundleResumeError'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { SwapExecutionError } from '@/lib/portal/swapFailure'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

type Props = {
  portfolioId: string
  portfolioName: string
  lockState: BundleInvestActiveLockPayload | null
  canExecute?: boolean
  hasUnallocatedCash: boolean
  onRefresh: () => void
  onLockRefresh: () => Promise<BundleInvestActiveLockPayload | null>
  onClose: () => void
}

function orderedRebalanceLegs(lines: PortfolioRebalancingAssetLine[]) {
  const sells = lines.filter((line) => line.action === 'sell')
  const buys = lines.filter((line) => line.action !== 'sell')
  return [...sells, ...buys]
}

function rebalanceExecutionPhaseLabel(phase: SwapExecutionPhase): string | null {
  switch (phase) {
    case 'verifying_price':
    case 'preparing':
      return BUNDLE_FLOW_UI.rebalancePreparingSecureConfirmation
    case 'approving':
    case 'signing':
    case 'submitting':
    case 'bridging':
      return BUNDLE_FLOW_UI.rebalanceExecutingSwap
    default:
      return null
  }
}

/** Rééquilibrage portefeuille — remplace reprise legacy LI.FI (R4.5 / V3 drift). */
export function PortalBundleAllocationActionsPanel({
  portfolioId,
  portfolioName,
  canExecute = true,
  hasUnallocatedCash,
  onRefresh,
  onLockRefresh,
  onClose,
}: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [assetLines, setAssetLines] = useState<PortfolioRebalancingAssetLine[]>([])
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [swapMockMode, setSwapMockMode] = useState(false)
  const [previewStatus, setPreviewStatus] = useState<string | null>(null)
  const [planningMode, setPlanningMode] = useState<string | null>(null)
  const [processingProgress, setProcessingProgress] = useState<BundleRebalancingProcessingProgress>({
    stage: 'preparing',
  })
  const [privyPrep, setPrivyPrep] = useState(false)
  const { privyReady } = usePortalAuthPrivy()
  const orderedLegs = useMemo(() => orderedRebalanceLegs(assetLines), [assetLines])

  const processingSteps = useMemo(
    () =>
      buildBundleRebalancingProcessingStepsDynamic({
        bundleLabel: portfolioName,
        legs: orderedLegs,
      }),
    [orderedLegs, portfolioName],
  )

  const processingStepStates = useMemo(
    () =>
      buildBundleRebalancingStepStates({
        legs: orderedLegs,
        assetLines,
        progress:
          executionPhase === 'preparing'
            ? { stage: 'preparing', legTotal: orderedLegs.length }
            : executionPhase === 'completed'
              ? { stage: 'completed', legTotal: orderedLegs.length }
              : processingProgress.stage === 'finalizing'
                ? { stage: 'finalizing', legTotal: orderedLegs.length }
                : processingProgress,
        executionPhase,
      }),
    [assetLines, executionPhase, orderedLegs, processingProgress],
  )

  const rawProgressIndex = useMemo(() => {
    const loadingIndex = processingStepStates.findIndex((state) => state === 'loading')
    if (loadingIndex >= 0) return loadingIndex
    const failedIndex = processingStepStates.findIndex((state) => state === 'failed')
    if (failedIndex >= 0) return failedIndex
    const doneCount = processingStepStates.filter((state) => state === 'done').length
    return Math.min(doneCount, Math.max(0, processingSteps.length - 1))
  }, [processingStepStates, processingSteps.length])

  const { runPortfolioRebalancing, inFlightRef } = useBundlePortfolioRebalancing(
    swapMockMode,
    'USDC',
    setExecutionPhase,
    (asset, status) => {
      setAssetLines((prev) => {
        const idx = prev.findIndex((l) => l.asset === asset)
        if (idx < 0) {
          return [...prev, { asset, action: 'buy', amount_entry: '0', status }]
        }
        const next = [...prev]
        next[idx] = { ...next[idx]!, status }
        return next
      })
    },
    (current, total, asset) => {
      setProcessingProgress({
        stage: 'executing',
        legCurrent: current,
        legTotal: total,
        activeAsset: asset,
      })
    },
  )

  useEffect(() => {
    fetchSupportedSwapAssets()
      .then((catalog) => setSwapMockMode(Boolean(catalog.mock_mode)))
      .catch(() => setSwapMockMode(false))
  }, [])

  useEffect(() => {
    if (busy || swapMockMode) {
      setPrivyPrep(false)
      return
    }

    let cancelled = false
    setPrivyPrep(true)
    void (async () => {
      try {
        await waitForPrivyClientReady(() => privyReady, { timeoutMs: 30_000 })
      } catch {
        /* l'exécution surfacera l'erreur */
      } finally {
        if (!cancelled) setPrivyPrep(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [busy, privyReady, swapMockMode])

  const loadPreview = async (options?: { throwOnError?: boolean }) => {
    setError(null)
    try {
      const preview = await previewPortfolioRebalancing(portfolioId)
      const plan = preview.rebalance_plan as
        | { status?: string; planning_mode?: string }
        | undefined
      setPreviewStatus(String(plan?.status ?? preview.status ?? 'ok'))
      setPlanningMode(plan?.planning_mode ?? null)
      setAssetLines(preview.asset_lines ?? [])
      return preview
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Estimation impossible'
      if (options?.throwOnError) {
        throw err instanceof Error ? err : new Error(message)
      }
      setError(message)
      return null
    }
  }

  useEffect(() => {
    void loadPreview()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount + portfolio change
  }, [portfolioId])

  const runRebalancing = async () => {
    if (busy || inFlightRef.current) return
    setBusy(true)
    setError(null)
    setProcessingProgress({ stage: 'preparing', legTotal: orderedLegs.length })
    setExecutionPhase('preparing')
    try {
      if (assetLines.length === 0) {
        await loadPreview({ throwOnError: true })
      }
      if (!swapMockMode) {
        await waitForPrivyClientReady(() => privyReady, { timeoutMs: 30_000 })
      }
      const result = await runPortfolioRebalancing(portfolioId)
      setAssetLines(result.asset_lines ?? assetLines)
      setProcessingProgress({ stage: 'finalizing', legTotal: orderedLegs.length })
      if (!isTerminalBundleV3Status(result.v3_status)) {
        setExecutionPhase('idle')
        if (result.v3_status === 'RUNNING') {
          setError(
            'Rééquilibrage partiellement terminé — relancez « Rééquilibrage » pour exécuter les swaps restants.',
          )
        } else {
          setError('Rééquilibrage non terminé — vérifiez l’état du portefeuille puis réessayez.')
        }
        await onLockRefresh()
        onRefresh()
        return
      }
      invalidatePortalCache('portal:crypto-wallet')
      await onLockRefresh()
      onRefresh()
      onClose()
    } catch (err) {
      setExecutionPhase('failed')
      const message =
        err instanceof SwapExecutionError
          ? err.userMessage
          : normalizeBundleResumeError(err)
      const isTimeout = /timed out|timeout|délai|abort|réseau blockchain/i.test(message)
      try {
        const reconciled = await reconcileStaleBundlePortfolioState(portfolioId, {
          forceSignableV3Close: isTimeout,
        })
        if (isTimeout && reconciled.active_operation?.status === 'none') {
          setError(
            'Préparation du swap trop longue — réessayez « Rééquilibrage » dans quelques secondes.',
          )
        } else {
          setError(message)
        }
      } catch {
        setError(message)
      }
      await onLockRefresh()
      onRefresh()
    } finally {
      setBusy(false)
      setProcessingProgress({ stage: 'preparing' })
    }
  }

  if (busy && processingSteps.length > 1) {
    return (
      <section className="flex w-full flex-col gap-3">
        <TransactionProcessingPage
          title="Rééquilibrage en cours"
          lead={`Rééquilibrage de ${portfolioName} — ventes puis achats vers l’allocation cible.`}
          steps={processingSteps}
          progressIndex={rawProgressIndex}
          completedProgressIndex={processingSteps.length}
          stepStates={processingStepStates}
          onClose={() => undefined}
          cardClassName="brw brw-proc v-card w-full"
        />

        {rebalanceExecutionPhaseLabel(executionPhase) ? (
          <p className="m-0 font-ui text-[13px] text-v-fg-muted">
            {rebalanceExecutionPhaseLabel(executionPhase)}
          </p>
        ) : null}

        {orderedLegs.length > 0 ? (
          <ul className="m-0 list-none space-y-1 rounded-v-input border border-v-border bg-v-card px-3 py-2 font-ui text-[13px] text-v-fg-body">
            {orderedLegs.map((line) => (
              <li key={`${line.action}-${line.asset}`}>{assetLineLabel(line)}</li>
            ))}
          </ul>
        ) : null}
      </section>
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-v-input border border-v-border bg-v-card px-3 py-3">
      {error ? <p className="m-0 font-ui text-[13px] text-v-error">{error}</p> : null}

      {previewStatus ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          Plan : {previewStatus}
          {previewStatus === 'no_action'
            ? ' — drift sous le minimum (1 USDC par leg), visualisation seule.'
            : null}
          {planningMode === 'portfolio_drift' || planningMode === 'portfolio_value_cash_deploy'
            ? ' — déploiement sur NAV totale (cash leg inclus)'
            : null}
        </p>
      ) : null}

      {assetLines.length > 0 ? (
        <ul className="m-0 list-none space-y-1 p-0 font-ui text-[13px] text-v-fg-body">
          {orderedLegs.map((line) => (
            <li key={`${line.action}-${line.asset}`}>{assetLineLabel(line)}</li>
          ))}
        </ul>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {privyPrep ? (
          <p
            className="m-0 flex w-full items-center gap-2 font-ui text-[13px] text-v-fg-muted"
            aria-live="polite"
          >
            <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
            {BUNDLE_FLOW_UI.rebalancePreparingSecureConfirmation}
          </p>
        ) : null}
        <AppButton
          type="button"
          variant="secondary"
          disabled={busy}
          onClick={() => void loadPreview()}
        >
          Estimer le plan
        </AppButton>
        <AppButton
          type="button"
          variant="primary"
          disabled={busy || !canExecute || previewStatus === 'no_action' || privyPrep}
          onClick={() => void runRebalancing()}
        >
          Rééquilibrage
        </AppButton>
        <AppButton type="button" variant="secondary" disabled={busy} onClick={onClose}>
          Fermer
        </AppButton>
      </div>

      <p className="m-0 font-ui text-[12px] text-v-fg-muted">
        {portfolioName}
        {hasUnallocatedCash
          ? ' — le cash leg sera réparti vers l’allocation cible (ventes puis achats, min. 1 USDC).'
          : ' — ajustement des positions vers l’allocation cible.'}
      </p>
    </div>
  )
}
