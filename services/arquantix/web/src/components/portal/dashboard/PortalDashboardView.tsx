'use client'

import { useMemo } from 'react'
import { PortalAccountsCard } from '@/components/portal/dashboard/PortalAccountsCard'
import { PortalDashboardHeader } from '@/components/portal/dashboard/PortalDashboardHeader'
import { PortalPortfolioHelpSection } from '@/components/portal/dashboard/PortalPortfolioHelpSection'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageSidebar } from '@/components/portal/PortalPageSidebar'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalNewsWidgetSection } from '@/components/portal/dashboard/PortalNewsWidgetSection'
import {
  applyWalletRowAccess,
  buildWalletRows,
  normalizeChartSeries,
  resolveHeaderBalance,
  resolvePerformanceChangeLabels,
  resolveReferenceCurrency,
  splitSavingsSummaryForDashboard,
} from '@/lib/portal/dashboardFormat'
import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'
import { resolveCreditLineFromPositions } from '@/lib/portal/lombard/lombardCreditLineFormat'
import { usePortalLombardPositions } from '@/lib/portal/lombard/usePortalLombardPositions'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import {
  isPortalChainDeFiEnabled,
  portalChainContextLabel,
} from '@/lib/portal/portalChainFilter'
import {
  filterCryptoSummaryByPortalScope,
  portalWalletScopeShortLabel,
} from '@/lib/portal/portalWalletScopeFilter'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import {
  shouldShowDashboardAccountsPending,
  shouldShowDashboardBalancePending,
} from '@/lib/portal/portalDashboardProgressiveData'
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
  const { chain } = usePortalChainContext()
  const { walletScope } = usePortalWalletScopeContext()
  const {
    positions: lombardPositions,
    loading: lombardLoading,
    enabled: lombardEnabled,
  } = usePortalLombardPositions()

  const derived = useMemo(() => {
    const currency = resolveReferenceCurrency(data)
    const chainLabel = portalChainContextLabel(chain)
    const walletLabel = portalWalletScopeShortLabel(walletScope)
    const filteredCrypto = filterCryptoSummaryByPortalScope(data.crypto, chain, walletScope)
    const savings = isPortalChainDeFiEnabled(chain) ? data.savings : null
    const { savingsVaults, exclusiveOfferVaults } = splitSavingsSummaryForDashboard(savings)

    const rows = applyWalletRowAccess(
      buildWalletRows(data.cash, filteredCrypto, data.placements, savings, currency).map((row) => {
        if (row.id === 'crypto') {
          const count = filteredCrypto?.summary?.positions_count ?? 0
          return {
            ...row,
            subtitle:
              count > 0
                ? `${count} asset${count === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
                : `No assets · ${chainLabel} · ${walletLabel}`,
          }
        }
        if (row.id === 'savings') {
          const count = savingsVaults?.positions_count ?? savingsVaults?.positions?.length ?? 0
          return {
            ...row,
            subtitle:
              count > 0
                ? `${count} vault${count === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
                : savings
                  ? `No vaults · ${chainLabel} · ${walletLabel}`
                  : row.subtitle,
          }
        }
        if (row.id === 'offers') {
          const defiCount =
            exclusiveOfferVaults?.positions_count ?? exclusiveOfferVaults?.positions?.length ?? 0
          const legacyCount = data.placements?.positions_count ?? 0
          const count = defiCount + legacyCount
          return {
            ...row,
            subtitle:
              count > 0
                ? `${count} exclusive offer${count === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
                : row.subtitle,
          }
        }
        return row
      }),
      data.profile,
      data.cash,
    )
    const balanceLabel = resolveHeaderBalance(data.globalStatistics, rows, currency, {
      scopedView: true,
    })
    const hasPrivyWallet = (data.privyPersonWallets?.wallets?.length ?? 0) > 0
    const depositHref = resolvePortalDepositHref(hasPrivyWallet)
    const chartValues = normalizeChartSeries(data.globalHistory?.points ?? [])
    const performance = resolvePerformanceChangeLabels(data.globalStatistics, currency)

    return {
      currency,
      rows,
      balanceLabel,
      depositHref,
      chartValues,
      performance,
      registrationProgress: data.profile?.registration_derived_progress_percent,
      registrationStepCompleted: data.profile?.registration_derived_completed_count,
      registrationStepTotal: data.profile?.registration_derived_total_count,
      chainLabel,
      walletLabel,
    }
  }, [data, chain, walletScope])

  const creditLine = useMemo(() => {
    if (!lombardEnabled) return null
    const summary = resolveCreditLineFromPositions(lombardPositions)
    if (!summary.visible && !lombardLoading) return null
    return {
      balanceLabel: summary.balanceLabel,
      subtitle: summary.subtitle,
      href: summary.href,
      pending: lombardLoading,
    }
  }, [lombardEnabled, lombardLoading, lombardPositions])

  const balancePending = shouldShowDashboardBalancePending({
    portfolioLoading,
    refreshing,
    data,
  })
  const accountsPending = shouldShowDashboardAccountsPending({
    portfolioLoading,
    refreshing,
    data,
  })

  return (
    <PortalPageContainer className={className}>
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalDashboardHeader
                balanceLabel={derived.balanceLabel}
                balancePending={balancePending}
                changeAmountLabel={derived.performance.amountLabel}
                changePercentLabel={derived.performance.percentLabel}
                changePositive={derived.performance.positive}
                depositHref={derived.depositHref}
                chartValues={derived.chartValues}
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalAccountsCard
                rows={derived.rows}
                creditLine={creditLine}
                portfolioPending={accountsPending}
                registrationProgressPercent={derived.registrationProgress}
                registrationStepCompleted={derived.registrationStepCompleted}
                registrationStepTotal={derived.registrationStepTotal}
              />
            </PortalReveal>

            <PortalReveal index={2}>
              <PortalNewsWidgetSection locale="en" initialData={data.newsWidget} />
            </PortalReveal>

            <PortalReveal index={3}>
              <PortalPortfolioHelpSection />
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
          </>
        }
        side={<PortalPageSidebar showPortrait showFeatured />}
      />
    </PortalPageContainer>
  )
}
