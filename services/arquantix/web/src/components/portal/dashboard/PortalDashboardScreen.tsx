'use client'

import { useMemo } from 'react'
import { PortalAccountsCard } from '@/components/portal/dashboard/PortalAccountsCard'
import { PortalDashboardHeader } from '@/components/portal/dashboard/PortalDashboardHeader'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalUnlockEuroBanner } from '@/components/portal/dashboard/PortalUnlockEuroBanner'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalNewsWidgetSection } from '@/components/portal/dashboard/PortalNewsWidgetSection'
import { Container } from '@/components/ui/Container'
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
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

const DASHBOARD_CACHE_KEY = 'portal:dashboard'

export function PortalDashboardScreen() {
  const { data, loading, refreshing, error, refresh } = usePortalCachedScreen<PortalDashboardPayload>({
    cacheKey: DASHBOARD_CACHE_KEY,
    url: '/api/portal/dashboard?locale=fr',
    ttlMs: 60_000,
    errorMessage: 'Unable to load your dashboard.',
  })

  const derived = useMemo(() => {
    if (!data) return null
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

    return {
      currency,
      rows,
      balanceLabel,
      performanceLabel: formatPerformancePct(performancePct),
      chartValues,
      displayName,
      showUnlockEuroBanner,
      registrationProgress: data.profile?.registration_derived_progress_percent,
    }
  }, [data])

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] items-center justify-center py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
      </Container>
    )
  }

  if (!data || !derived) return null

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
          <PortalReveal index={0}>
            <PortalDashboardHeader
              displayName={derived.displayName}
              balanceLabel={derived.balanceLabel}
              performanceLabel={derived.performanceLabel}
              chartValues={derived.chartValues}
              className="pt-0"
            />
          </PortalReveal>

          {derived.showUnlockEuroBanner ? (
            <PortalReveal index={1}>
              <PortalUnlockEuroBanner progressPercent={derived.registrationProgress} />
            </PortalReveal>
          ) : null}

          <PortalReveal index={2}>
            <PortalAccountsCard rows={derived.rows} />
          </PortalReveal>

          <PortalReveal index={3}>
            <PortalNewsWidgetSection locale="fr" initialData={data.newsWidget} />
          </PortalReveal>

          {data.partial ? (
            <p className="m-0 font-ui text-[12px] text-v-fg-muted">
              Some portfolio data could not be loaded. Refresh or check the API.
            </p>
          ) : null}

          <button
            type="button"
            disabled={refreshing}
            onClick={() => void refresh()}
            className="v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px] disabled:opacity-50"
          >
            {refreshing ? 'Refreshing…' : 'Refresh dashboard'}
          </button>
        </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
