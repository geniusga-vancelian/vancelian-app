'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { PortalLazyBundleAllocationActions } from '@/components/portal/bundles/PortalLazyBundleAllocationActions'
import { AppButton } from '@/components/design-system/app/AppButton'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  fetchActiveBundleInvestLock,
  type BundleInvestActiveLockPayload,
} from '@/lib/portal/bundleClient'
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

/** Allocation wallet bundle — rééquilibrage uniquement (plus de reprise legacy LI.FI). */
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
  const legacyLockActive = lockState?.status === 'active'

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

  if (!hasUnallocatedCash && !legacyLockActive && !loadingLock) {
    return null
  }

  const showRebalancingEntry = hasUnallocatedCash || legacyLockActive

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title="Allocation" />
      {loadingLock ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">Vérification de l’état du panier…</p>
      ) : null}

      {hasUnallocatedCash ? (
        <p className="m-0 font-ui text-[13px] text-v-fg-muted">
          Cash leg non alloué : {formatCryptoMoney(cashLegDisplayValue, currency)} en attente de
          répartition vers les actifs cibles.
        </p>
      ) : null}

      {legacyLockActive ? (
        <div className="rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-900">
          <p className="m-0 font-medium">Allocation incomplète</p>
          <p className="mt-1 mb-0 text-[12px]">
            Un ancien investissement legacy est en attente. Utilisez le rééquilibrage pour répartir le
            cash leg — la reprise manuelle n’est plus proposée.
          </p>
        </div>
      ) : null}

      {showRebalancingEntry && !actionsOpen ? (
        <AppButton type="button" variant="primary" onClick={() => setActionsOpen(true)}>
          Rééquilibrage
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
          hasUnallocatedCash={hasUnallocatedCash || legacyLockActive}
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
