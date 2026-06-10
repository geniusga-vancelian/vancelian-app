'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

import {
  assetLineLabel,
  useBundlePortfolioRebalancing,
} from '@/components/portal/bundles/useBundlePortfolioRebalancing'
import { AppButton } from '@/components/design-system/app/AppButton'
import {
  previewPortfolioRebalancing,
  reconcileStaleBundlePortfolioState,
  type BundleInvestActiveLockPayload,
  type PortfolioRebalancingAssetLine,
} from '@/lib/portal/bundleClient'
import { isTerminalBundleV3Status } from '@/components/portal/transaction/mappers/bundleSteps'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

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
  )

  useEffect(() => {
    fetchSupportedSwapAssets()
      .then((catalog) => setSwapMockMode(Boolean(catalog.mock_mode)))
      .catch(() => setSwapMockMode(false))
  }, [])

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
    setExecutionPhase('preparing')
    try {
      if (assetLines.length === 0) {
        await loadPreview({ throwOnError: true })
      }
      const result = await runPortfolioRebalancing(portfolioId)
      setAssetLines(result.asset_lines ?? assetLines)
      if (result.v3_status === 'RUNNING') {
        throw new Error(
          'Rééquilibrage interrompu — rouvrez le panier pour reprendre la signature.',
        )
      }
      invalidatePortalCache('portal:crypto-wallet')
      await onLockRefresh()
      onRefresh()
      onClose()
    } catch (err) {
      setExecutionPhase('failed')
      const message = err instanceof Error ? err.message : 'Rééquilibrage impossible'
      setError(message)
      try {
        await reconcileStaleBundlePortfolioState(portfolioId, {
          forceSignableV3Close: /timed out|timeout|indisponible|signature/i.test(message),
        })
      } catch {
        // best-effort cleanup
      }
      await onLockRefresh()
      onRefresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-v-input border border-v-border bg-v-card px-3 py-3">
      {busy ? (
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-5 w-5 animate-spin text-v-fg-muted" />
          <span className="font-ui text-[13px] text-v-fg">
            {executionPhase === 'signing'
              ? 'Signature portefeuille…'
              : executionPhase === 'submitting'
                ? 'Confirmation on-chain…'
                : 'Rééquilibrage en cours…'}
          </span>
        </div>
      ) : null}

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
          {assetLines.map((line) => (
            <li key={`${line.action}-${line.asset}`}>{assetLineLabel(line)}</li>
          ))}
        </ul>
      ) : null}

      <div className="flex flex-wrap gap-2">
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
          disabled={busy || !canExecute || previewStatus === 'no_action'}
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
