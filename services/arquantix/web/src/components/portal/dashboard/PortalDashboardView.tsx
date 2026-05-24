'use client'

import { useMemo } from 'react'
import { PortalAccountsCard } from '@/components/portal/dashboard/PortalAccountsCard'
import { PortalDashboardHeader } from '@/components/portal/dashboard/PortalDashboardHeader'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalUnlockEuroBanner } from '@/components/portal/dashboard/PortalUnlockEuroBanner'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalNewsWidgetSection } from '@/components/portal/dashboard/PortalNewsWidgetSection'
import {
  applyWalletRowAccess,
  buildWalletRows,
  formatPerformancePct,
  normalizeChartSeries,
  resolveDisplayName,
  resolveHeaderBalance,
  resolvePerformancePct,
  resolveReferenceCurrency,
  shouldShowUnlockEuroBanner,
} from '@/lib/portal/dashboardFormat'
import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'
import { resolvePortalDepositHref } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  data: PortalDashboardPayload
  portfolioLoading?: boolean
  refreshing?: boolean
  onRefresh?: () => void
  showRefreshLink?: boolean
  className?: string
}

export function PortalDashboardView({
  data,
  portfolioLoading = false,
  refreshing = false,
  onRefresh,
  showRefreshLink = true,
  className,
}: Props) {
  const derived = useMemo(() => {
    const currency = resolveReferenceCurrency(data)
    const rows = applyWalletRowAccess(
      buildWalletRows(data.cash, data.crypto, data.placements, currency),
      data.profile,
      data.cash,
    )
    const balanceLabel = resolveHeaderBalance(data.globalStatistics, rows, currency)
    const performancePct = resolvePerformancePct(data.globalStatistics)
    const chartValues = normalizeChartSeries(data.globalHistory?.points ?? [])
    const displayName = resolveDisplayName(data)
    const showUnlockEuroBanner = shouldShowUnlockEuroBanner(data.profile)
    const hasPrivyWallet = (data.privyPersonWallets?.wallets?.length ?? 0) > 0
    const depositHref = resolvePortalDepositHref(hasPrivyWallet)

    return {
      currency,
      rows,
      balanceLabel,
      performanceLabel: formatPerformancePct(performancePct),
      chartValues,
      displayName,
      showUnlockEuroBanner,
      depositHref,
      registrationProgress: data.profile?.registration_derived_progress_percent,
    }
  }, [data])

  return (
    <PortalPageContainer className={className}>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <PortalDashboardHeader
            displayName={derived.displayName}
            balanceLabel={derived.balanceLabel}
            performanceLabel={derived.performanceLabel}
            chartValues={derived.chartValues}
            depositHref={derived.depositHref}
            className="pt-0"
          />
        </PortalReveal>

        {derived.showUnlockEuroBanner ? (
          <PortalReveal index={1}>
            <PortalUnlockEuroBanner progressPercent={derived.registrationProgress} />
          </PortalReveal>
        ) : null}

        <PortalReveal index={2}>
          <PortalAccountsCard rows={derived.rows} portfolioPending={portfolioLoading} />
        </PortalReveal>

        <PortalReveal index={3}>
          <PortalNewsWidgetSection locale="fr" initialData={data.newsWidget} />
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Some portfolio data could not be loaded. Refresh or check the API.
          </p>
        ) : null}

        {showRefreshLink && onRefresh ? (
          <button
            type="button"
            disabled={refreshing}
            onClick={() => void onRefresh()}
            className={cn(
              'v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50',
            )}
          >
            {refreshing ? 'Refreshing…' : 'Refresh dashboard'}
          </button>
        ) : null}
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
