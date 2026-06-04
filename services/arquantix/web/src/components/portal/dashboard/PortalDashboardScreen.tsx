'use client'

import { Container } from '@/components/ui/Container'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalDashboardView } from '@/components/portal/dashboard/PortalDashboardView'
import { shouldShowDashboardFullSkeleton } from '@/lib/portal/portalDashboardProgressiveData'
import { usePortalDashboardProgressive } from '@/lib/portal/usePortalDashboardProgressive'

export function PortalDashboardScreen() {
  const { data, loading, portfolioLoading, refreshing, error, refresh } =
    usePortalDashboardProgressive()

  if (shouldShowDashboardFullSkeleton(loading, data)) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] items-center justify-center py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
      </Container>
    )
  }

  if (!data) return null

  return (
    <PortalDashboardView
      data={data}
      portfolioLoading={portfolioLoading}
      refreshing={refreshing}
      onRefresh={() => void refresh()}
    />
  )
}
