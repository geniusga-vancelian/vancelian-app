'use client'

import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { normalizeNavPath } from '@/components/site/NavPendingContext'
import { PORTAL_PATH_PREFIX, PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

function ShimmerBlock({ className }: { className?: string }) {
  return <div className={cn('portal-shimmer', className)} aria-hidden />
}

function TwoColumnSkeleton({ children }: { children: React.ReactNode }) {
  return (
    <PortalPageContainer>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16">
        <div className="space-y-6">{children}</div>
        <ShimmerBlock className="hidden h-56 rounded-v-card lg:block" />
      </div>
    </PortalPageContainer>
  )
}

export function PortalDashboardSkeleton() {
  return (
    <TwoColumnSkeleton>
      <ShimmerBlock className="h-8 w-48 rounded-v-input" />
      <ShimmerBlock className="h-52 rounded-v-card" />
      <ShimmerBlock className="h-10 w-full max-w-md rounded-v-pill" />
      <ShimmerBlock className="h-64 rounded-v-card" />
    </TwoColumnSkeleton>
  )
}

export function PortalMarketsSkeleton() {
  return (
    <TwoColumnSkeleton>
      <ShimmerBlock className="h-24 rounded-v-card" />
      <ShimmerBlock className="h-72 rounded-v-card" />
      <ShimmerBlock className="h-56 rounded-v-card" />
    </TwoColumnSkeleton>
  )
}

export function PortalInvestSkeleton() {
  return (
    <TwoColumnSkeleton>
      <ShimmerBlock className="h-40 rounded-v-card" />
      <ShimmerBlock className="h-72 rounded-v-card" />
      <ShimmerBlock className="h-80 rounded-v-card" />
    </TwoColumnSkeleton>
  )
}

export function PortalProfileSkeleton() {
  return (
    <PortalPageContainer>
      <div className="mx-auto max-w-2xl space-y-6">
        <ShimmerBlock className="h-8 w-32 rounded-v-input" />
        <ShimmerBlock className="h-24 rounded-v-card" />
        <ShimmerBlock className="h-40 rounded-v-card" />
        <ShimmerBlock className="h-48 rounded-v-card" />
      </div>
    </PortalPageContainer>
  )
}

export function PortalGenericSkeleton() {
  return (
    <PortalPageContainer>
      <div className="mx-auto max-w-2xl space-y-4">
        <ShimmerBlock className="h-8 w-40 rounded-v-input" />
        <ShimmerBlock className="h-32 rounded-v-card" />
      </div>
    </PortalPageContainer>
  )
}

/** Skeleton immédiat affiché au clic menu, avant le montage de la page cible. */
export function PortalRouteSkeleton({ route }: { route: string }) {
  const normalized = normalizeNavPath(route)

  if (
    normalized === PORTAL_ROUTES.dashboard ||
    normalized === PORTAL_PATH_PREFIX
  ) {
    return <PortalDashboardSkeleton />
  }
  if (normalized === PORTAL_ROUTES.markets || normalized.startsWith(`${PORTAL_ROUTES.markets}/`)) {
    return <PortalMarketsSkeleton />
  }
  if (normalized === PORTAL_ROUTES.invest || normalized.startsWith(`${PORTAL_ROUTES.invest}/`)) {
    return <PortalInvestSkeleton />
  }
  if (normalized === PORTAL_ROUTES.profile) {
    return <PortalProfileSkeleton />
  }
  if (normalized === PORTAL_ROUTES.myWallets) {
    return <PortalGenericSkeleton />
  }
  if (
    normalized === PORTAL_ROUTES.cryptoWallet ||
    normalized.startsWith(`${PORTAL_ROUTES.cryptoWallet}/`)
  ) {
    return <PortalDashboardSkeleton />
  }

  return <PortalGenericSkeleton />
}
