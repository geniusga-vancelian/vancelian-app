'use client'

import { useMemo } from 'react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalAccountsCard } from '@/components/portal/dashboard/PortalAccountsCard'
import { PortalDashboardHeader } from '@/components/portal/dashboard/PortalDashboardHeader'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalNewsWidgetSection } from '@/components/portal/dashboard/PortalNewsWidgetSection'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  buildWalletRows,
  formatPerformancePct,
  normalizeChartSeries,
  resolveDisplayName,
  resolveHeaderBalance,
  resolvePerformancePct,
  resolveReferenceCurrency,
  shouldShowActivationModule,
  shouldShowMyAccountsCard,
  hasEuroCashAccount,
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
    const rows = buildWalletRows(data.cash, data.crypto, data.placements, currency)
    const balanceLabel = resolveHeaderBalance(data.globalStatistics, rows, currency)
    const performancePct = resolvePerformancePct(data.globalStatistics)
    const chartValues = normalizeChartSeries(data.globalHistory?.points ?? [])
    const displayName = resolveDisplayName(data)
    const showAccounts = shouldShowMyAccountsCard(data.profile, hasEuroCashAccount(data.cash))
    const showActivation = shouldShowActivationModule(data.profile)

    return {
      currency,
      rows,
      balanceLabel,
      performanceLabel: formatPerformancePct(performancePct),
      chartValues,
      displayName,
      showAccounts,
      showActivation,
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

          {derived.showActivation ? (
            <PortalReveal index={1}>
              <article className="rounded-v-card border border-v-fg-10 bg-v-card p-4 shadow-v-subtle sm:p-5">
                <VEyebrow className="mb-2">Get started</VEyebrow>
                <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
                  Complete your activation journey to unlock investing on Vancelian.
                </p>
                <Button type="button" className="mt-4 w-full sm:w-auto">
                  Continue activation
                </Button>
              </article>
            </PortalReveal>
          ) : null}

          {derived.showAccounts ? (
            <PortalReveal index={2}>
              <PortalAccountsCard rows={derived.rows} />
            </PortalReveal>
          ) : null}

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
