'use client'

import { useCallback, useEffect, useState } from 'react'

import { PortalLazyBundleAllocationActions } from '@/components/portal/bundles/PortalLazyBundleAllocationActions'
import { AppButton } from '@/components/design-system/app/AppButton'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  fetchActiveBundleInvestLock,
  preflightPortfolioRebalancing,
  type BundleInvestActiveLockPayload,
  type PortfolioRebalancingPreflightPayload,
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

function blockerMessage(
  blockers: PortfolioRebalancingPreflightPayload['blockers'],
): string | null {
  const codes = (blockers ?? []).map((b) => b.code)
  if (codes.includes('portfolio_financial_operation_in_progress')) {
    return 'Une opération financière est déjà en cours sur ce portefeuille.'
  }
  if (codes.includes('ambiguous_legacy_batches')) {
    return 'Batch legacy ambigu — contactez le support avant rééquilibrage.'
  }
  if (codes.includes('v3_deposit_batch_in_progress')) {
    return 'Un dépôt V3 est encore en cours sur ce bundle.'
  }
  if (codes.length > 0) {
    return `Blocage : ${codes.join(', ')}`
  }
  return null
}

/** Allocation wallet bundle — entrée rééquilibrage toujours visible (estimation + exécution). */
export function PortalBundleAllocationReadOnlyPanel({
  portfolioId,
  portfolioName,
  currency,
  cashLegDisplayValue,
  onRefresh,
}: Props) {
  const [lockState, setLockState] = useState<BundleInvestActiveLockPayload | null>(null)
  const [loadingLock, setLoadingLock] = useState(true)
  const [loadingPreflight, setLoadingPreflight] = useState(true)
  const [preflight, setPreflight] = useState<PortfolioRebalancingPreflightPayload | null>(null)
  const [preflightError, setPreflightError] = useState<string | null>(null)
  const [actionsOpen, setActionsOpen] = useState(false)

  const legacyLockActive = lockState?.status === 'active'
  const legacyLockAmbiguous = lockState?.status === 'ambiguous'
  const hasCashLeg = cashLegDisplayValue > 0.001

  const planStatus = String(
    preflight?.rebalance_plan?.status ?? preflight?.status ?? 'unknown',
  )
  const canExecute = Boolean(preflight?.can_execute)
  const wouldAbandonLegacy = Boolean(preflight?.would_abandon_legacy_lock)
  const blockerText = blockerMessage(preflight?.blockers)

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
    setPreflightError(null)
    try {
      const result = await preflightPortfolioRebalancing(portfolioId)
      setPreflight(result)
    } catch (err) {
      setPreflight(null)
      setPreflightError(err instanceof Error ? err.message : 'Analyse drift impossible')
    } finally {
      setLoadingPreflight(false)
    }
  }, [portfolioId])

  useEffect(() => {
    void refreshLock()
    void loadPreflight()
  }, [loadPreflight, refreshLock])

  const cashLegHint = (() => {
    if (loadingPreflight) return 'analyse en cours…'
    if (preflightError) return 'analyse indisponible — utilisez « Estimer le plan ».'
    if (planStatus === 'ok' && canExecute) {
      return 'répartition vers les actifs cibles recommandée.'
    }
    if (planStatus === 'no_action') {
      return 'drift sous le minimum (1 USDC par leg) — estimation du plan toujours disponible.'
    }
    if (planStatus === 'ok' && !canExecute) {
      return 'plan calculé — exécution bloquée (voir message ci-dessous).'
    }
    return 'estimation du plan disponible pour visualiser le drift.'
  })()

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Allocation" />

      {loadingLock || loadingPreflight ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Analyse du portefeuille…</p>
      ) : null}

      {hasCashLeg ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Cash leg : {formatCryptoMoney(cashLegDisplayValue, currency)} — {cashLegHint}
        </p>
      ) : (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Ajustement des positions vers l&apos;allocation cible — estimation disponible.
        </p>
      )}

      {preflightError ? (
        <p className="m-0 font-ui text-[13px] text-v-error">{preflightError}</p>
      ) : null}

      {blockerText ? (
        <p className="m-0 font-ui text-[13px] text-amber-800">{blockerText}</p>
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

      {!actionsOpen && !loadingPreflight ? (
        <div className="flex flex-wrap gap-2">
          <AppButton type="button" variant="secondary" onClick={() => setActionsOpen(true)}>
            Estimer le plan
          </AppButton>
          <AppButton
            type="button"
            variant="primary"
            disabled={!canExecute}
            onClick={() => canExecute && setActionsOpen(true)}
          >
            {wouldAbandonLegacy
              ? 'Rééquilibrage (abandon legacy + déploiement cash)'
              : 'Rééquilibrage'}
          </AppButton>
        </div>
      ) : null}

      {!canExecute && !loadingPreflight && !actionsOpen ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          {planStatus === 'no_action'
            ? 'Exécution désactivée : aucune leg ≥ 1 USDC. « Estimer le plan » affiche quand même le drift.'
            : 'Exécution désactivée — « Estimer le plan » reste disponible pour visualiser le drift.'}
        </p>
      ) : null}

      {actionsOpen ? (
        <PortalLazyBundleAllocationActions
          portfolioId={portfolioId}
          portfolioName={portfolioName}
          lockState={lockState}
          canExecute={canExecute}
          hasUnallocatedCash={hasCashLeg || canExecute || legacyLockActive}
          onRefresh={onRefresh}
          onLockRefresh={refreshLock}
          onClose={() => setActionsOpen(false)}
        />
      ) : null}

      {!actionsOpen ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          {portfolioName} — rééquilibrage automatique vers l&apos;allocation cible (ventes puis
          achats, min. 1 USDC par leg).
        </p>
      ) : null}
    </section>
  )
}
