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
  normalizeChartSeries,
  resolveBalanceCardIdentity,
  resolveHeaderBalance,
  resolvePerformanceChangeLabels,
  resolveReferenceCurrency,
  shouldShowUnlockEuroBanner,
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
    const identity = resolveBalanceCardIdentity(data)
    const showUnlockEuroBanner = shouldShowUnlockEuroBanner(data.profile)
    const hasPrivyWallet = (data.privyPersonWallets?.wallets?.length ?? 0) > 0
    const depositHref = resolvePortalDepositHref(hasPrivyWallet)
    const chartValues = normalizeChartSeries(data.globalHistory?.points ?? [])
    const performance = resolvePerformanceChangeLabels(data.globalStatistics, currency)
    const showChart = true

    return {
      currency,
      rows,
      balanceLabel,
      identity,
      showUnlockEuroBanner,
      depositHref,
      chartValues,
      performance,
      showChart,
      registrationProgress: data.profile?.registration_derived_progress_percent,
      chainLabel,
      walletLabel,
    }
  }, [data, chain, walletScope])

  return (
    <PortalPageContainer className={className}>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <PortalDashboardHeader
            welcomeName={derived.identity.displayName}
            showAvatar={derived.identity.showAvatar}
            avatarInitials={derived.identity.avatarInitials}
            avatarImageUrl={derived.identity.avatarImageUrl}
            balanceLabel={derived.balanceLabel}
            balancePending={portfolioLoading || refreshing}
            changeAmountLabel={derived.performance.amountLabel}
            changePercentLabel={derived.performance.percentLabel}
            changePositive={derived.performance.positive}
            chartValues={derived.chartValues}
            showChart={derived.showChart}
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
          <PortalAccountsCard rows={derived.rows} portfolioPending={portfolioLoading || refreshing} />
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
