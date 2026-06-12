'use client'

import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/button'
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
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" variant="outline" onClick={() => void refresh()}>
          Try again
        </Button>
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
