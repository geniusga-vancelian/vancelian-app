'use client'

import { useCallback, useEffect, useState } from 'react'

import { PortalLazyBundleAllocationActions } from '@/components/portal/bundles/PortalLazyBundleAllocationActions'
import { AppButton } from '@/components/design-system/app/AppButton'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  fetchActiveBundleInvestLock,
  preflightPortfolioRebalancing,
  type BundleInvestActiveLockPayload,
} from '@/lib/portal/bundleClient'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'

type Props = {
  portfolioId: string
  portfolioName: string
  positions?: unknown
  currency: string
  cashLegDisplayValue: number
  onRefresh: () => void
}

/** Allocation wallet bundle — rééquilibrage uniquement (plus de reprise legacy LI.FI). */
export function PortalBundleAllocationReadOnlyPanel({
  portfolioId,
  portfolioName,
  currency,
  cashLegDisplayValue,
  onRefresh,
}: Props) {
  const [lockState, setLockState] = useState<BundleInvestActiveLockPayload | null>(null)
  const [loadingLock, setLoadingLock] = useState(true)
  const [loadingPreflight, setLoadingPreflight] = useState(false)
  const [driftActionable, setDriftActionable] = useState(false)
  const [preflightStatus, setPreflightStatus] = useState<string | null>(null)
  const [wouldAbandonLegacy, setWouldAbandonLegacy] = useState(false)
  const [actionsOpen, setActionsOpen] = useState(false)

  const legacyLockActive = lockState?.status === 'active'
  const legacyLockAmbiguous = lockState?.status === 'ambiguous'
  const hasMaterialCash = cashLegDisplayValue > 1

  const refreshLock = useCallback(async () => {
    setLoadingLock(true)
    try {
      const active = await fetchActiveBundleInvestLock(portfolioId)
      setLockState(active)
      return active
    } catch {
      setLockState(null)
      return null
    } finally {
      setLoadingLock(false)
    }
  }, [portfolioId])

  const loadPreflight = useCallback(async () => {
    setLoadingPreflight(true)
    try {
      const preflight = await preflightPortfolioRebalancing(portfolioId)
      const planStatus = String(
        preflight.rebalance_plan?.status ?? preflight.status ?? 'no_action',
      )
      setPreflightStatus(planStatus)
      setWouldAbandonLegacy(Boolean(preflight.would_abandon_legacy_lock))
      setDriftActionable(
        Boolean(preflight.can_execute) ||
          (planStatus === 'ok' && (preflight.blockers?.length ?? 0) === 0),
      )
    } catch {
      setPreflightStatus(null)
      setDriftActionable(false)
    } finally {
      setLoadingPreflight(false)
    }
  }, [portfolioId])

  useEffect(() => {
    void refreshLock()
  }, [refreshLock])

  useEffect(() => {
    if (hasMaterialCash || legacyLockActive || legacyLockAmbiguous) {
      void loadPreflight()
    }
  }, [hasMaterialCash, legacyLockActive, legacyLockAmbiguous, loadPreflight])

  const showRebalancingEntry =
    driftActionable || legacyLockActive || legacyLockAmbiguous || hasMaterialCash

  if (!showRebalancingEntry && !loadingLock && !loadingPreflight) {
    return null
  }

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Allocation" />
      {loadingLock || loadingPreflight ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Analyse du portefeuille…</p>
      ) : null}

      {hasMaterialCash ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Cash leg : {formatCryptoMoney(cashLegDisplayValue, currency)}
          {driftActionable
            ? ' — répartition vers les actifs cibles recommandée.'
            : ' — en attente d’analyse drift.'}
        </p>
      ) : null}

      {wouldAbandonLegacy || legacyLockActive || legacyLockAmbiguous ? (
        <div className="rounded-v-input border border-sky-200 bg-sky-50 px-3 py-2 font-ui text-[13px] text-sky-950">
          <p className="m-0 font-medium">Ancien investissement détecté</p>
          <p className="mt-1 mb-0 text-[12px]">
            Un batch legacy (ex. swap CBETH en attente) sera{' '}
            <strong>automatiquement abandonné</strong> lors du rééquilibrage. Le cash leg (
            {formatCryptoMoney(cashLegDisplayValue, currency)}) sera ensuite réparti vers les actifs
            cibles — aucune reprise manuelle requise.
          </p>
        </div>
      ) : null}

      {preflightStatus === 'ok' && driftActionable && !actionsOpen ? (
        <AppButton type="button" variant="primary" onClick={() => setActionsOpen(true)}>
          {wouldAbandonLegacy ? 'Rééquilibrage (abandon legacy + déploiement cash)' : 'Rééquilibrage'}
        </AppButton>
      ) : null}

      {showRebalancingEntry && preflightStatus !== 'ok' && !actionsOpen && !loadingPreflight ? (
        <AppButton type="button" variant="secondary" onClick={() => void loadPreflight()}>
          Vérifier le rééquilibrage
        </AppButton>
      ) : null}

      {actionsOpen ? (
        <PortalLazyBundleAllocationActions
          portfolioId={portfolioId}
          portfolioName={portfolioName}
          lockState={lockState}
          hasUnallocatedCash={driftActionable || legacyLockActive || hasMaterialCash}
          onRefresh={onRefresh}
          onLockRefresh={refreshLock}
          onClose={() => setActionsOpen(false)}
        />
      ) : null}

      {!actionsOpen ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          {portfolioName} — rééquilibrage automatique vers l’allocation cible (ventes puis achats).
        </p>
      ) : null}
    </section>
  )
}
