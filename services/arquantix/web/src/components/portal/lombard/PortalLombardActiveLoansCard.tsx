'use client'

import { Loader2 } from 'lucide-react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { Button } from '@/components/ui/button'
import { formatLombardPercent } from '@/lib/portal/lombard/lombardFormat'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  shouldShowLombardActiveLoanCard,
  shouldShowLombardEmptyState,
  shouldShowLombardWalletDashboardCard,
} from '@/lib/portal/lombard/lombardPositionVisibility'
import { usePortalLombardPositions } from '@/lib/portal/lombard/usePortalLombardPositions'
import { useLombardV1PortalEnabled } from '@/lib/portal/lombard/useLombardV1PortalEnabled'
import { portalBorrowRoute, portalLombardPositionRoute } from '@/lib/portal/portalRouting'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'

function healthTone(status: LombardActivePosition['healthStatus']): string {
  if (status === 'comfortable') return 'text-emerald-700'
  if (status === 'monitor') return 'text-amber-700'
  if (status === 'risky' || status === 'blocked') return 'text-red-700'
  return 'text-v-fg'
}

function LombardPositionRow({ position }: { position: LombardActivePosition }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-v-border bg-v-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">
            {position.collateralDisplayName} guarantee
          </p>
          <p className="m-0 mt-1 font-ui text-[13px] text-v-muted">
            {position.collateralAmount} {position.collateralSymbol}
          </p>
        </div>
        <PortalNavLink
          href={portalLombardPositionRoute({ marketId: position.marketId })}
          className="shrink-0 font-ui text-[13px] text-v-accent no-underline hover:underline"
        >
          View details
        </PortalNavLink>
      </div>
      <dl className="m-0 grid gap-2 font-ui text-[14px]">
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Amount borrowed</dt>
          <dd className="m-0 font-medium text-v-fg">{position.borrowAmount} USDC</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Safety level</dt>
          <dd className={`m-0 font-medium ${healthTone(position.healthStatus)}`}>{position.healthLabel}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Current usage</dt>
          <dd className="m-0 font-medium text-v-fg">{formatLombardPercent(position.currentLtvPercent)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-v-muted">Interest rate</dt>
          <dd className="m-0 font-medium text-v-fg">{position.borrowApyLabel}</dd>
        </div>
      </dl>
    </div>
  )
}

type Props = {
  walletPositions: PortalCryptoPosition[]
}

export function PortalLombardActiveLoansCard({ walletPositions }: Props) {
  const { chain } = usePortalExecutionScope()
  const { enabled: lombardEnabled, loading: featureLoading } = useLombardV1PortalEnabled()
  const { positions, loading, error } = usePortalLombardPositions()

  if (!shouldShowLombardWalletDashboardCard({ lombardEnabled, chain, loading: featureLoading })) {
    return null
  }

  if (loading && positions.length === 0) {
    return (
      <section className="flex items-center gap-2 text-v-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="font-ui text-[14px]">Loading your loan…</span>
      </section>
    )
  }

  if (error) {
    return (
      <section className="rounded-2xl border border-v-border bg-v-surface p-4">
        <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
      </section>
    )
  }

  if (shouldShowLombardActiveLoanCard(positions)) {
    return (
      <section className="flex w-full flex-col gap-3">
        <AppSectionHeader title="Your active loan" />
        <p className="m-0 font-ui text-[14px] text-v-muted">
          Borrowed USDC backed by your Bitcoin or Ethereum
        </p>
        <div className="flex flex-col gap-3">
          {positions.map((position) => (
            <LombardPositionRow key={position.marketId} position={position} />
          ))}
        </div>
      </section>
    )
  }

  if (shouldShowLombardEmptyState({ positions, walletPositions })) {
    return (
      <section className="flex w-full flex-col gap-3 rounded-2xl border border-v-border bg-v-surface p-5">
        <AppSectionHeader title="Your active loan" />
        <p className="m-0 font-ui text-[14px] text-v-muted">No active loan yet</p>
        <p className="m-0 font-ui text-[14px] leading-relaxed text-v-muted">
          You can borrow USDC without selling your Bitcoin or Ethereum.
        </p>
        <PortalNavLink href={portalBorrowRoute()} className="no-underline">
          <Button type="button" className="w-full sm:w-auto">
            Borrow USDC
          </Button>
        </PortalNavLink>
      </section>
    )
  }

  return null
}
