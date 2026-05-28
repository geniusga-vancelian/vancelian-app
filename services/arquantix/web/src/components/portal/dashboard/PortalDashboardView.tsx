'use client'

import { useMemo } from 'react'
import {
  SupportAsidePanel,
  hasSupportAsideContent,
} from '@/components/design-system/SupportAsidePanel'
import { PortalAccountsCard } from '@/components/portal/dashboard/PortalAccountsCard'
import { PortalDashboardHeader } from '@/components/portal/dashboard/PortalDashboardHeader'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalNewsWidgetSection } from '@/components/portal/dashboard/PortalNewsWidgetSection'
import { PortalAdvisorBanner } from '@/components/portal/PortalAdvisorBanner'
import { usePortalSupportContent } from '@/components/portal/PortalSupportContentProvider'
import {
  applyWalletRowAccess,
  buildWalletRows,
  normalizeChartSeries,
  resolveHeaderBalance,
  resolvePerformanceChangeLabels,
  resolveReferenceCurrency,
} from '@/lib/portal/dashboardFormat'
import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'
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
  const cmsSupport = usePortalSupportContent()
  const showSupportAside = hasSupportAsideContent(cmsSupport)

  const derived = useMemo(() => {
    const currency = resolveReferenceCurrency(data)
    const chainLabel = portalChainContextLabel(chain)
    const walletLabel = portalWalletScopeShortLabel(walletScope)
    const filteredCrypto = filterCryptoSummaryByPortalScope(data.crypto, chain, walletScope)
    const savings = isPortalChainDeFiEnabled(chain) ? data.savings : null

    const rows = applyWalletRowAccess(
      buildWalletRows(data.cash, filteredCrypto, data.placements, savings, currency).map((row) => {
        if (row.id === 'crypto') {
          const count = filteredCrypto?.summary?.positions_count ?? 0
          return {
            ...row,
            subtitle:
              count > 0
                ? `${count} actif${count === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
                : `Aucun actif · ${chainLabel} · ${walletLabel}`,
          }
        }
        if (row.id === 'savings' && savings) {
          const count = savings.positions_count ?? savings.positions?.length ?? 0
          return {
            ...row,
            subtitle:
              count > 0
                ? `${count} vault${count === 1 ? '' : 's'} · ${chainLabel} · ${walletLabel}`
                : `Aucun vault · ${chainLabel} · ${walletLabel}`,
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

  const portfolioPending = portfolioLoading || refreshing

  return (
    <PortalPageContainer className={className}>
      <PortalPortfolioLayout
        main={
          <>
            <PortalReveal index={0}>
              <PortalDashboardHeader
                balanceLabel={derived.balanceLabel}
                balancePending={portfolioPending}
                changeAmountLabel={derived.performance.amountLabel}
                changePositive={derived.performance.positive}
                depositHref={derived.depositHref}
                chartValues={derived.chartValues}
                className="pt-0"
              />
            </PortalReveal>

            <PortalReveal index={1}>
              <PortalAccountsCard
                rows={derived.rows}
                portfolioPending={portfolioPending}
                registrationProgressPercent={derived.registrationProgress}
                registrationStepCompleted={derived.registrationStepCompleted}
                registrationStepTotal={derived.registrationStepTotal}
              />
            </PortalReveal>

            <PortalReveal index={2}>
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
          </>
        }
        side={
          <>
            <PortalAdvisorBanner />
            {showSupportAside ? (
              <SupportAsidePanel support={cmsSupport} stickyTopClassName="static" className="static" />
            ) : null}
          </>
        }
      />
    </PortalPageContainer>
  )
}
