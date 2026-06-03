'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { PortalLazyBundleAllocationActions } from '@/components/portal/bundles/PortalLazyBundleAllocationActions'
import { AppButton } from '@/components/design-system/app/AppButton'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  fetchActiveBundleInvestLock,
  type BundleInvestActiveLockPayload,
} from '@/lib/portal/bundleClient'
import { bundleLockStatusLabel } from '@/lib/portal/bundleInvestLabels'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'
import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'

type Props = {
  portfolioId: string
  portfolioName: string
  positions: PortalBundlePosition[] | undefined
  currency: string
  cashLegDisplayValue: number
  onRefresh: () => void
}

/** Allocation wallet bundle — lecture seule + CTA vers actions lazy (R4.5-F5-B). */
export function PortalBundleAllocationReadOnlyPanel({
  portfolioId,
  portfolioName,
  positions,
  currency,
  cashLegDisplayValue,
  onRefresh,
}: Props) {
  const [lockState, setLockState] = useState<BundleInvestActiveLockPayload | null>(null)
  const [loadingLock, setLoadingLock] = useState(true)
  const [actionsOpen, setActionsOpen] = useState(false)

  const spotNotional = useMemo(
    () =>
      (positions ?? [])
        .filter((p) => p.positionType === 'spot' && p.quantity > 0)
        .reduce((sum, p) => sum + (p.marketValue ?? p.costBasis ?? 0), 0),
    [positions],
  )

  const hasUnallocatedCash = cashLegDisplayValue > 1 && spotNotional < cashLegDisplayValue * 0.25

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

  useEffect(() => {
    void refreshLock()
  }, [refreshLock])

  if (!hasUnallocatedCash && lockState?.status !== 'active' && !loadingLock) {
    return null
  }

  const lockActive = lockState?.status === 'active'
  const canResume = lockActive && (lockState?.resume_available ?? true)
  const showActionsEntry = canResume || hasUnallocatedCash

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Allocation" />
      {loadingLock ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Vérification de l’état investissement…</p>
      ) : null}

      {hasUnallocatedCash ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Cash leg non alloué : {formatCryptoMoney(cashLegDisplayValue, currency)} en attente de
          répartition vers les actifs cibles.
        </p>
      ) : null}

      {lockActive && lockState?.lock ? (
        <div className="rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-900">
          <p className="m-0 font-medium">Investissement en cours</p>
          <p className="mt-1 mb-0 text-[12px]">
            Batch {lockState.lock.batch_id.slice(0, 8)}… —{' '}
            {bundleLockStatusLabel(lockState.lock.status)}
          </p>
          {lockState.reconciled ? (
            <p className="mt-1 mb-0 text-[12px]">Verrou obsolète nettoyé automatiquement.</p>
          ) : null}
        </div>
      ) : null}

      {showActionsEntry && !actionsOpen ? (
        <AppButton type="button" variant="primary" onClick={() => setActionsOpen(true)}>
          {canResume && hasUnallocatedCash
            ? 'Reprendre ou réallouer'
            : canResume
              ? 'Reprendre l’investissement'
              : 'Réallouer le cash'}
        </AppButton>
      ) : null}

      {actionsOpen && lockState !== null ? (
        <PortalLazyBundleAllocationActions
          portfolioId={portfolioId}
          portfolioName={portfolioName}
          positions={positions}
          currency={currency}
          cashLegDisplayValue={cashLegDisplayValue}
          lockState={lockState}
          hasUnallocatedCash={hasUnallocatedCash}
          onRefresh={onRefresh}
          onLockRefresh={refreshLock}
          onClose={() => setActionsOpen(false)}
        />
      ) : null}

      {!actionsOpen ? (
        <p className="m-0 font-ui text-[12px] text-v-fg-muted">
          {portfolioName} — les actions d’allocation chargent le portefeuille de signature uniquement
          après confirmation.
        </p>
      ) : null}
    </section>
  )
}
