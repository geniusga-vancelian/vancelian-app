'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  assetLineLabel,
  useBundlePortfolioRebalancing,
} from '@/components/portal/bundles/useBundlePortfolioRebalancing'
import { AppButton } from '@/components/design-system/app/AppButton'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import {
  buildBundleActiveOperationSteps,
  bundleActiveOperationProgressIndex,
  isTerminalBundleV3Status,
} from '@/components/portal/transaction/mappers/bundleSteps'
import { BUNDLE_FLOW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import {
  fetchActiveBundleOperation,
  reconcileStaleBundlePortfolioState,
  resumePortfolioRebalancing,
  submitBundleLegTx,
  type BundleActiveOperationPayload,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { abandonSwap } from '@/lib/portal/swapClient'
import { resumeActiveBundleOperation } from '@/lib/portal/bundleActiveOperationResume'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { usePortalAuthPrivy } from '@/components/portal/PortalAuthPrivyGate'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'

const POLL_MS = 5000

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

type Props = {
  portfolioId: string
  portfolioName: string
  onRefresh: () => void
  onActiveChange?: (active: boolean) => void
}

function allocationAssetsFromLines(lines: PortfolioRebalancingAssetLine[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const line of lines) {
    const asset = line.asset?.trim()
    if (!asset || seen.has(asset)) continue
    seen.add(asset)
    out.push(asset)
  }
  return out
}

function toResumePayload(
  active: BundleActiveOperationPayload,
): PortfolioRebalancingPayload | null {
  if (active.v3_status !== 'RUNNING' && !active.rebalance_execution_id) {
    return null
  }
  return {
    portfolio_id: active.portfolio_id,
    status: 'running',
    v3_status: active.v3_status ?? 'RUNNING',
    rebalance_execution_id: active.rebalance_execution_id,
    asset_lines: active.asset_lines,
    sell_results: active.sell_results,
    buy_results: active.buy_results,
  }
}

function hasSignablePendingLegs(
  payload: PortfolioRebalancingPayload | BundleActiveOperationPayload | null,
): boolean {
  if (!payload) return false
  const legs = [...(payload.sell_results ?? []), ...(payload.buy_results ?? [])]
  return legs.some(
    (leg) =>
      leg.status === 'pending' &&
      Boolean(leg.swap_id) &&
      (leg.error === 'awaiting_client_signature' ||
        leg.error === 'awaiting_wallet_signature' ||
        leg.error === 'awaiting_confirmation'),
  )
}

/** Suivi d’une opération bundle en cours — steps persistés côté worker, reprise signature manuelle. */
export function PortalBundleActiveOperationPanel({
  portfolioId,
  portfolioName,
  onRefresh,
  onActiveChange,
}: Props) {
  const [active, setActive] = useState<BundleActiveOperationPayload | null>(null)
  const [assetLines, setAssetLines] = useState<PortfolioRebalancingAssetLine[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resuming, setResuming] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [swapMockMode, setSwapMockMode] = useState(false)
  const { privyReady } = usePortalAuthPrivy()
  const resumeStartedRef = useRef(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const terminalHandledRef = useRef(false)

  const { signAndSubmit, pollUntilTerminal } = useLifiSwapExecution(
    swapMockMode,
    setExecutionPhase,
    'USDC',
    { submitTx: submitBundleLegTx },
  )

  const { inFlightRef } = useBundlePortfolioRebalancing(swapMockMode, 'USDC')

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const handleTerminal = useCallback(() => {
    if (terminalHandledRef.current) return
    terminalHandledRef.current = true
    clearPoll()
    invalidatePortalCache('portal:crypto-wallet')
    onRefresh()
  }, [clearPoll, onRefresh])

  const loadActive = useCallback(async (): Promise<BundleActiveOperationPayload | null> => {
    try {
      const payload = await fetchActiveBundleOperation(portfolioId)
      setActive(payload)
      const lines =
        payload.plan_stale && payload.current_asset_lines?.length
          ? payload.current_asset_lines
          : payload.asset_lines
      if (lines?.length) {
        setAssetLines(lines)
      }
      if (payload.status === 'none' || isTerminalBundleV3Status(payload.v3_status)) {
        if (payload.status === 'active' && isTerminalBundleV3Status(payload.v3_status)) {
          handleTerminal()
        } else {
          clearPoll()
        }
      }
      return payload
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger l’opération en cours')
      return null
    } finally {
      setLoading(false)
    }
  }, [clearPoll, handleTerminal, portfolioId])

  const tryResume = useCallback(
    async (payload: BundleActiveOperationPayload) => {
      if (resumeStartedRef.current || inFlightRef.current || resuming) return
      if (payload.v3_status !== 'RUNNING') return

      const initial = toResumePayload(payload)
      if (!initial) return

      resumeStartedRef.current = true
      inFlightRef.current = true
      setResuming(true)
      setError(null)

      try {
        setExecutionPhase('preparing')
        if (!swapMockMode && hasSignablePendingLegs(initial)) {
          await waitForPrivyClientReady(() => privyReady, { timeoutMs: 30_000 })
        }
        let result: PortfolioRebalancingPayload

        if (hasSignablePendingLegs(initial)) {
          if (payload.plan_stale) {
            result = await resumePortfolioRebalancing(portfolioId)
            setAssetLines(result.asset_lines ?? [])
          } else {
            result = await resumeActiveBundleOperation({
              initial,
              signAndSubmit,
              pollUntilTerminal,
              onPhaseChange: setExecutionPhase,
              onAssetLines: setAssetLines,
            })
          }
        } else {
          result = await resumePortfolioRebalancing(portfolioId)
          setAssetLines(result.asset_lines ?? [])
        }

        setActive((prev) =>
          prev
            ? {
                ...prev,
                v3_status: result.v3_status,
                asset_lines: result.asset_lines,
                sell_results: result.sell_results,
                buy_results: result.buy_results,
                plan_stale: false,
              }
            : prev,
        )

        if (isTerminalBundleV3Status(result.v3_status)) {
          handleTerminal()
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Reprise impossible'
        const isSigningTimeout =
          /timed out|timeout|délai|abort/i.test(message) ||
          executionPhase === 'signing'
        if (isSigningTimeout) {
          const pendingLeg = [...(initial.sell_results ?? []), ...(initial.buy_results ?? [])].find(
            (leg) => leg.status === 'pending' && leg.swap_id,
          )
          try {
            if (pendingLeg?.swap_id) {
              await abandonSwap(pendingLeg.swap_id, {
                reason: 'client_signature_timeout',
                failure_phase: 'sign',
              })
            }
            const reconciled = await reconcileStaleBundlePortfolioState(portfolioId, {
              forceSignableV3Close: true,
            })
            if (
              reconciled.active_operation?.status === 'none' ||
              isTerminalBundleV3Status(reconciled.active_operation?.v3_status)
            ) {
              setActive(reconciled.active_operation)
              handleTerminal()
              setError(null)
            } else {
              setError('Signature expirée — opération clôturée partiellement.')
              await loadActive()
            }
          } catch {
            setError(message)
          }
        } else if (message !== 'plan_hash_changed') {
          setError(message)
        }
        resumeStartedRef.current = false
      } finally {
        inFlightRef.current = false
        setResuming(false)
      }
    },
    [handleTerminal, inFlightRef, pollUntilTerminal, portfolioId, privyReady, resuming, signAndSubmit, swapMockMode],
  )

  useEffect(() => {
    fetchSupportedSwapAssets()
      .then((catalog) => setSwapMockMode(Boolean(catalog.mock_mode)))
      .catch(() => setSwapMockMode(false))
  }, [])

  useEffect(() => {
    resumeStartedRef.current = false
    terminalHandledRef.current = false
    setLoading(true)
    setError(null)
    void loadActive().then((payload) => {
      if (payload?.status === 'active' && !isTerminalBundleV3Status(payload.v3_status)) {
        clearPoll()
        pollRef.current = setInterval(() => {
          void loadActive()
        }, POLL_MS)
        if (hasSignablePendingLegs(payload)) {
          void tryResume(payload)
        }
      }
    })
    return () => clearPoll()
  }, [clearPoll, loadActive, portfolioId, tryResume])

  const showPanel =
    !loading &&
    active?.status === 'active' &&
    !isTerminalBundleV3Status(active.v3_status)

  const prevShowPanelRef = useRef(false)
  useEffect(() => {
    if (prevShowPanelRef.current !== showPanel) {
      prevShowPanelRef.current = showPanel
      onActiveChange?.(showPanel)
    }
  }, [onActiveChange, showPanel])

  const allocationAssets = useMemo(
    () => allocationAssetsFromLines(assetLines),
    [assetLines],
  )

  const includeFundingStep = active?.operation_type === 'v3_deposit_rebalance'

  const steps = useMemo(
    () =>
      buildBundleActiveOperationSteps({
        bundleLabel: portfolioName,
        operationType: active?.operation_type ?? 'v3_deposit_rebalance',
        allocationAssets,
        includeFundingStep,
      }),
    [active?.operation_type, allocationAssets, includeFundingStep, portfolioName],
  )

  const progressIndex = useMemo(
    () =>
      bundleActiveOperationProgressIndex({
        v3Status: active?.v3_status,
        assetLines,
        stepCount: steps.length,
        includeFundingStep,
      }),
    [active?.v3_status, assetLines, includeFundingStep, steps.length],
  )

  const needsUserResume = hasSignablePendingLegs(active)

  if (!showPanel) {
    return null
  }

  const lead =
    active?.operation_type === 'v3_deposit_rebalance'
      ? BUNDLE_FLOW_UI.processingLead(
          active.funding_amount ? `${active.funding_amount} USDC` : '—',
          portfolioName,
        )
      : `Rééquilibrage de ${portfolioName} en cours.`

  return (
    <section className="flex w-full flex-col gap-3">
      <TransactionProcessingPage
        title={
          active?.operation_type === 'portfolio_rebalancing'
            ? 'Rééquilibrage en cours'
            : BUNDLE_FLOW_UI.processingTitle
        }
        lead={lead}
        steps={steps}
        progressIndex={progressIndex}
        completedProgressIndex={Math.max(0, progressIndex - 1)}
        onClose={() => undefined}
        cardClassName="brw brw-proc v-card w-full"
      />

        {rebalanceExecutionPhaseLabel(executionPhase) ? (
          <p className="m-0 font-ui text-[13px] text-v-fg-muted">
            {rebalanceExecutionPhaseLabel(executionPhase)}
          </p>
        ) : null}

      {assetLines.length > 0 ? (
        <ul className="m-0 list-none space-y-1 rounded-v-input border border-v-border bg-v-card px-3 py-2 font-ui text-[13px] text-v-fg-body">
          {assetLines.map((line) => (
            <li key={`${line.action}-${line.asset}`}>{assetLineLabel(line)}</li>
          ))}
        </ul>
      ) : null}

      {needsUserResume && !resuming ? (
        <AppButton
          type="button"
          variant="primary"
          disabled={resuming}
          onClick={() => active && void tryResume(active)}
        >
          Reprendre la signature
        </AppButton>
      ) : null}

      {!needsUserResume && active?.v3_status === 'RUNNING' && !resuming ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          Traitement en cours — les étapes se mettent à jour automatiquement.
        </p>
      ) : null}

      {resuming ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Reprise en cours…</p>
      ) : null}

      {error ? <p className="m-0 font-ui text-[13px] text-v-error">{error}</p> : null}

      {active?.message ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">{active.message}</p>
      ) : null}
    </section>
  )
}
