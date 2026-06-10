'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  assetLineLabel,
  useBundlePortfolioRebalancing,
} from '@/components/portal/bundles/useBundlePortfolioRebalancing'
import { TransactionProcessingPage } from '@/components/portal/transaction/TransactionProcessingPage'
import {
  buildBundleActiveOperationSteps,
  bundleActiveOperationProgressIndex,
  isTerminalBundleV3Status,
} from '@/components/portal/transaction/mappers/bundleSteps'
import { BUNDLE_FLOW_UI } from '@/components/portal/transaction/mappers/bundleUiCopy'
import {
  fetchActiveBundleOperation,
  resumePortfolioRebalancing,
  submitBundleLegTx,
  type BundleActiveOperationPayload,
  type PortfolioRebalancingAssetLine,
  type PortfolioRebalancingPayload,
} from '@/lib/portal/bundleClient'
import { resumeActiveBundleOperation } from '@/lib/portal/bundleActiveOperationResume'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import { useLifiSwapExecution } from '@/components/portal/swap/useLifiSwapExecution'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

const POLL_MS = 4000

type Props = {
  portfolioId: string
  portfolioName: string
  onRefresh: () => void
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

function hasPendingClientLegs(payload: PortfolioRebalancingPayload | null): boolean {
  if (!payload) return false
  const legs = [...(payload.sell_results ?? []), ...(payload.buy_results ?? [])]
  return legs.some((leg) => leg.status === 'pending' && Boolean(leg.swap_id))
}

/** Reprise automatique d’un worker bundle (dépôt V3 ou rééquilibrage) — même UX que l’invest. */
export function PortalBundleActiveOperationPanel({
  portfolioId,
  portfolioName,
  onRefresh,
}: Props) {
  const [active, setActive] = useState<BundleActiveOperationPayload | null>(null)
  const [assetLines, setAssetLines] = useState<PortfolioRebalancingAssetLine[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [swapMockMode, setSwapMockMode] = useState(false)
  const resumeStartedRef = useRef(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
    clearPoll()
    invalidatePortalCache('portal:crypto-wallet')
    onRefresh()
  }, [clearPoll, onRefresh])

  const loadActive = useCallback(async (): Promise<BundleActiveOperationPayload | null> => {
    try {
      const payload = await fetchActiveBundleOperation(portfolioId)
      setActive(payload)
      if (payload.asset_lines?.length) {
        setAssetLines(payload.asset_lines)
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
      if (resumeStartedRef.current || inFlightRef.current) return
      if (payload.v3_status !== 'RUNNING') return

      const initial = toResumePayload(payload)
      if (!initial) return

      resumeStartedRef.current = true
      inFlightRef.current = true
      setError(null)

      try {
        setExecutionPhase('preparing')
        let result: PortfolioRebalancingPayload

        if (hasPendingClientLegs(initial)) {
          result = await resumeActiveBundleOperation({
            initial,
            signAndSubmit,
            pollUntilTerminal,
            onPhaseChange: setExecutionPhase,
            onAssetLines: setAssetLines,
          })
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
              }
            : prev,
        )

        if (isTerminalBundleV3Status(result.v3_status)) {
          handleTerminal()
        } else if (hasPendingClientLegs(result)) {
          resumeStartedRef.current = false
          void tryResume({
            ...payload,
            v3_status: result.v3_status,
            asset_lines: result.asset_lines,
            sell_results: result.sell_results,
            buy_results: result.buy_results,
          })
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Reprise impossible'
        if (message !== 'plan_hash_changed') {
          setError(message)
        }
        resumeStartedRef.current = false
      } finally {
        inFlightRef.current = false
      }
    },
    [handleTerminal, inFlightRef, pollUntilTerminal, portfolioId, signAndSubmit],
  )

  useEffect(() => {
    fetchSupportedSwapAssets()
      .then((catalog) => setSwapMockMode(Boolean(catalog.mock_mode)))
      .catch(() => setSwapMockMode(false))
  }, [])

  useEffect(() => {
    resumeStartedRef.current = false
    setLoading(true)
    void loadActive().then((payload) => {
      if (payload?.status === 'active' && !isTerminalBundleV3Status(payload.v3_status)) {
        clearPoll()
        pollRef.current = setInterval(() => {
          void loadActive()
        }, POLL_MS)
        void tryResume(payload)
      }
    })
    return () => clearPoll()
  }, [clearPoll, loadActive, portfolioId, tryResume])

  const showPanel =
    !loading &&
    active?.status === 'active' &&
    !isTerminalBundleV3Status(active.v3_status)

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
        steps={steps.map((step) => ({ name: step.label, body: step.subtext }))}
        progressIndex={progressIndex}
        completedProgressIndex={Math.max(0, progressIndex - 1)}
        onClose={() => undefined}
        cardClassName="brw brw-proc v-card w-full"
      />

      {executionPhase === 'signing' ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Signature portefeuille requise…</p>
      ) : null}

      {assetLines.length > 0 ? (
        <ul className="m-0 list-none space-y-1 rounded-v-input border border-v-border bg-v-card px-3 py-2 font-ui text-[13px] text-v-fg-body">
          {assetLines.map((line) => (
            <li key={`${line.action}-${line.asset}`}>{assetLineLabel(line)}</li>
          ))}
        </ul>
      ) : null}

      {error ? <p className="m-0 font-ui text-[13px] text-v-error">{error}</p> : null}

      {active?.message ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">{active.message}</p>
      ) : null}
    </section>
  )
}
