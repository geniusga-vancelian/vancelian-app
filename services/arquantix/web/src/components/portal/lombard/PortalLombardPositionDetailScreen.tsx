'use client'

import { ArrowLeft, Loader2 } from 'lucide-react'
import { useMemo } from 'react'
import { useSearchParams } from 'next/navigation'

import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { Button } from '@/components/ui/button'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { formatLombardPercent } from '@/lib/portal/lombard/lombardFormat'
import { findLombardPositionByCollateral, findLombardPositionByMarketId } from '@/lib/portal/lombard/lombardPositionLookup'
import { usePortalLombardPositions } from '@/lib/portal/lombard/usePortalLombardPositions'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

const LIQUIDATION_EXPLAINER =
  'If the value of your guarantee falls too much, part of your crypto may be sold automatically to repay the loan.'

export function PortalLombardPositionDetailScreen() {
  const searchParams = useSearchParams()
  const { positions, loading, error, refresh } = usePortalLombardPositions()

  const position = useMemo(() => {
    const marketId = searchParams?.get('marketId')?.trim()
    const collateral = searchParams?.get('collateral')?.trim()
    if (marketId) return findLombardPositionByMarketId(positions, marketId)
    if (collateral) return findLombardPositionByCollateral(positions, collateral)
    return positions[0] ?? null
  }, [positions, searchParams])

  if (loading && !position) {
    return (
      <PortalPageContainer>
        <div className="flex items-center gap-2 text-v-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="font-ui text-[14px]">Loading your loan…</span>
        </div>
      </PortalPageContainer>
    )
  }

  if (error) {
    return (
      <PortalPageContainer>
        <p className="font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void refresh()}>
          Retry
        </Button>
      </PortalPageContainer>
    )
  }

  if (!position) {
    return (
      <PortalPageContainer>
        <PortalPageIntro
          eyebrow="Loan"
          title="No active loan"
          description="You do not have an active Lombard loan on this wallet."
        />
        <PortalNavLink href={PORTAL_ROUTES.borrow} className="no-underline">
          <Button type="button">Borrow USDC</Button>
        </PortalNavLink>
      </PortalPageContainer>
    )
  }

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalNavLink
          href={PORTAL_ROUTES.cryptoWallet}
          className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
        >
          <ArrowLeft className="h-4 w-4" />
          Crypto wallet
        </PortalNavLink>

        <PortalPageIntro
          eyebrow="Your loan"
          title="Your active loan"
          description={`USDC borrowed against your ${position.collateralDisplayName}.`}
        />

        <section className="rounded-2xl border border-v-border bg-v-surface p-5">
          <dl className="m-0 grid gap-4 font-ui text-[15px]">
            <div>
              <dt className="text-v-muted">Your guarantee</dt>
              <dd className="m-0 mt-1 font-medium text-v-fg">
                {position.collateralAmount} {position.collateralSymbol}
                {position.collateralUsdValue ? ` · ≈ ${position.collateralUsdValue} USDC` : ''}
              </dd>
            </div>
            <div>
              <dt className="text-v-muted">Your borrowed USDC</dt>
              <dd className="m-0 mt-1 font-medium text-v-fg">{position.borrowAmount} USDC</dd>
            </div>
            <div>
              <dt className="text-v-muted">Safety level</dt>
              <dd className="m-0 mt-1 font-medium text-v-fg">
                {position.healthLabel} — {position.healthMessage}
              </dd>
            </div>
            <div>
              <dt className="text-v-muted">Current usage of your borrowing capacity</dt>
              <dd className="m-0 mt-1 font-medium text-v-fg">
                {formatLombardPercent(position.currentLtvPercent)} · max {position.maxUserLtvPercent}%
              </dd>
            </div>
            <div>
              <dt className="text-v-muted">Interest rate</dt>
              <dd className="m-0 mt-1 font-medium text-v-fg">{position.borrowApyLabel}</dd>
            </div>
            <div>
              <dt className="text-v-muted">What could trigger liquidation</dt>
              <dd className="m-0 mt-1 text-v-fg">{LIQUIDATION_EXPLAINER}</dd>
              {position.liquidationPrice ? (
                <dd className="m-0 mt-2 text-[14px] text-v-muted">
                  Estimated liquidation zone around {position.liquidationPrice} per{' '}
                  {position.collateralSymbol} · Morpho threshold {position.morphoLltvPercent}%
                </dd>
              ) : null}
            </div>
          </dl>
          <p className="m-0 mt-4 font-ui text-[12px] text-v-muted">{VANCELIAN_LOMBARD_V1.poweredByLabel}</p>
        </section>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
