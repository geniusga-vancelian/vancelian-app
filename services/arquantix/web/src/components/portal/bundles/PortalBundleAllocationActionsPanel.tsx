'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useBundleLifiInvest } from '@/components/portal/bundles/useBundleLifiInvest'
import { useBundleLifiRebalance } from '@/components/portal/bundles/useBundleLifiRebalance'
import { AppButton } from '@/components/design-system/app/AppButton'
import {
  previewBundleRebalance,
  resumeBundleInvest,
  type BundleInvestActiveLockPayload,
  type BundleRebalancePreviewPayload,
} from '@/lib/portal/bundleClient'
import {
  saveBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type Props = {
  portfolioId: string
  portfolioName: string
  positions: PortalBundlePosition[] | undefined
  currency: string
  cashLegDisplayValue: number
  lockState: BundleInvestActiveLockPayload | null
  hasUnallocatedCash: boolean
  onRefresh: () => void
  onLockRefresh: () => Promise<BundleInvestActiveLockPayload | null>
  onClose: () => void
}

/** Resume / rebalance — hooks LI.FI montés sous PortalWeb3BoundaryLazy (R4.5-F5-B). */
export function PortalBundleAllocationActionsPanel({
  portfolioId,
  portfolioName,
  lockState,
  hasUnallocatedCash,
  onRefresh,
  onLockRefresh,
  onClose,
}: Props) {
  const [preview, setPreview] = useState<BundleRebalancePreviewPayload | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [legLabel, setLegLabel] = useState<string | null>(null)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [swapMockMode, setSwapMockMode] = useState(false)

  const { resumeSession: resumeInvest, inFlightRef: investInFlight } = useBundleLifiInvest(
    swapMockMode,
    'USDC',
    setExecutionPhase,
    (current, total, asset) => setLegLabel(`Leg ${current}/${total} — ${asset}`),
  )

  const { runRebalance, inFlightRef: rebalanceInFlight } = useBundleLifiRebalance(
    swapMockMode,
    'USDC',
    setExecutionPhase,
    (current, total, asset) => setLegLabel(`Leg ${current}/${total} — ${asset}`),
  )

  useEffect(() => {
    fetchSupportedSwapAssets()
      .then((catalog) => setSwapMockMode(Boolean(catalog.mock_mode)))
      .catch(() => setSwapMockMode(false))
  }, [])

  const loadPreview = async () => {
    setLoadingPreview(true)
    setError(null)
    try {
      const result = await previewBundleRebalance(portfolioId)
      setPreview(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prévisualisation impossible')
    } finally {
      setLoadingPreview(false)
    }
  }

  const runResumeInvest = async () => {
    if (busy || investInFlight.current) return
    setBusy(true)
    setError(null)
    setExecutionPhase('preparing')
    try {
      const invest = await resumeBundleInvest(portfolioId)
      const session: BundleInvestSession = {
        portfolioId,
        batchId: invest.batch_id,
        fundingAsset: lockState?.lock?.funding_asset ?? invest.entry_asset,
        fundingAmount: Number(lockState?.lock?.funding_amount ?? invest.total_entry_asset_received),
        invest,
        savedAt: new Date().toISOString(),
      }
      saveBundleInvestSession(session)
      await resumeInvest(session)
      invalidatePortalCache('portal:crypto-wallet')
      await onLockRefresh()
      onRefresh()
      onClose()
    } catch (err) {
      setExecutionPhase('failed')
      setError(err instanceof Error ? err.message : 'Reprise impossible')
    } finally {
      setBusy(false)
      setLegLabel(null)
    }
  }

  const runReallocate = async () => {
    if (busy || rebalanceInFlight.current) return
    setBusy(true)
    setError(null)
    setExecutionPhase('preparing')
    try {
      await runRebalance(portfolioId)
      invalidatePortalCache('portal:crypto-wallet')
      await onLockRefresh()
      onRefresh()
      setPreview(null)
      onClose()
    } catch (err) {
      setExecutionPhase('failed')
      setError(err instanceof Error ? err.message : 'Réallocation impossible')
    } finally {
      setBusy(false)
      setLegLabel(null)
    }
  }

  const lockActive = lockState?.status === 'active'
  const canResume = lockActive && (lockState?.resume_available ?? true)
  const buyCount = preview?.buy_plan?.length ?? 0

  return (
    <div className="flex flex-col gap-3 rounded-v-input border border-v-border bg-v-card px-3 py-3">
      {busy ? (
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-5 w-5 animate-spin text-v-fg-muted" />
          <span className="font-ui text-[13px] text-v-fg">{legLabel ?? executionPhase}</span>
        </div>
      ) : null}

      {error ? <p className="m-0 font-ui text-[13px] text-v-error">{error}</p> : null}

      <div className="flex flex-wrap gap-2">
        {canResume ? (
          <AppButton type="button" variant="primary" disabled={busy} onClick={() => void runResumeInvest()}>
            Reprendre l’investissement
          </AppButton>
        ) : null}
        {hasUnallocatedCash ? (
          <>
            <AppButton
              type="button"
              variant="secondary"
              disabled={busy || loadingPreview}
              onClick={() => void loadPreview()}
            >
              {loadingPreview ? 'Estimation…' : 'Prévisualiser réallocation'}
            </AppButton>
            <AppButton
              type="button"
              variant="primary"
              disabled={busy || (preview != null && buyCount === 0 && preview.status === 'no_action')}
              onClick={() => void runReallocate()}
            >
              Réallouer le cash USDC
            </AppButton>
          </>
        ) : null}
        <AppButton type="button" variant="outline" disabled={busy} onClick={onClose}>
          Fermer
        </AppButton>
      </div>

      {preview ? (
        <div className="rounded-v-input border border-v-fg-10 bg-v-bg px-3 py-2 font-ui text-[12px] text-v-fg-body">
          <p className="m-0">
            Plan : {preview.status}
            {buyCount > 0 ? ` · ${buyCount} achat${buyCount > 1 ? 's' : ''}` : ''}
          </p>
          {preview.warnings?.length ? (
            <p className="mt-1 mb-0 text-amber-800">{preview.warnings.join(' · ')}</p>
          ) : null}
        </div>
      ) : null}

      <p className="m-0 font-ui text-[12px] text-v-fg-muted">
        {portfolioName} — si l’allocation échoue, vous pouvez réallouer le cash leg ou retirer vers
        Mon Trading ci-dessous.
      </p>
    </div>
  )
}
