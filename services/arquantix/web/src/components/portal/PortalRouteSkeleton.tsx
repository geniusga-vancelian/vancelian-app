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

/** Placeholder section Markets différée (news, research, sidebar). */
export function PortalMarketsSectionSkeleton({
  variant = 'default',
}: {
  variant?: 'default' | 'compact' | 'sidebar'
}) {
  if (variant === 'sidebar') {
    return <ShimmerBlock className="h-56 rounded-v-card" aria-hidden />
  }
  if (variant === 'compact') {
    return <ShimmerBlock className="h-40 rounded-v-card" aria-hidden />
  }
  return <ShimmerBlock className="h-48 rounded-v-card" aria-hidden />
}

/** Skeleton grille 2 cartes pour une section Placer (paniers, coffres, DeFi). */
export function PortalPlacerSectionSkeleton({ cards = 2 }: { cards?: number }) {
  return (
    <div className="placer-grid placer-grid--2" aria-busy="true" aria-label="Loading section">
      {Array.from({ length: cards }, (_, i) => (
        <ShimmerBlock key={i} className="min-h-[360px] rounded-v-card" />
      ))}
    </div>
  )
}

export function PortalInvestSkeleton() {
  return (
    <PortalPageContainer>
      <div className="portal-placer-grid">
        <div className="col-main space-y-10">
          <ShimmerBlock className="aspect-[21/9] min-h-[280px] rounded-v-card" />
          <ShimmerBlock className="h-9 w-full max-w-md rounded-v-pill" />
          <ShimmerBlock className="h-10 w-64 rounded-v-input" />
          <PortalPlacerSectionSkeleton />
        </div>
        <ShimmerBlock className="col-side hidden h-20 rounded-v-card lg:block" />
      </div>
    </PortalPageContainer>
  )
}

export function PortalProfileSkeletonBlocks() {
  return (
    <div className="space-y-6">
      <ShimmerBlock className="h-8 w-32 rounded-v-input" />
      <ShimmerBlock className="h-24 rounded-v-card" />
      <ShimmerBlock className="h-40 rounded-v-card" />
      <ShimmerBlock className="h-48 rounded-v-card" />
    </div>
  )
}

export function PortalProfileSkeleton() {
  return (
    <PortalPageContainer>
      <div className="mx-auto max-w-2xl">
        <PortalProfileSkeletonBlocks />
      </div>
    </PortalPageContainer>
  )
}

export function PortalAcademySkeleton() {
  return (
    <PortalPageContainer>
      <div className="portal-placer-grid">
        <div className="col-main space-y-6">
          <ShimmerBlock className="h-12 max-w-xl rounded-v-pill" />
          <ShimmerBlock className="h-80 rounded-v-card" />
          <ShimmerBlock className="h-10 w-full max-w-lg rounded-v-pill" />
          <div className="grid grid-cols-1 gap-5 min-[880px]:grid-cols-2 min-[1200px]:grid-cols-3">
            <ShimmerBlock className="h-72 rounded-v-card" />
            <ShimmerBlock className="h-72 rounded-v-card" />
            <ShimmerBlock className="h-72 rounded-v-card" />
          </div>
          <ShimmerBlock className="h-32 rounded-v-card" />
        </div>
        <ShimmerBlock className="col-side hidden h-80 rounded-v-card lg:block" />
      </div>
    </PortalPageContainer>
  )
}

/** Squelette page article (lecture) — titre, cover, paragraphes + sidebar. */
export function PortalArticleSkeleton() {
  return (
    <PortalPageContainer>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16">
        <div className="space-y-5">
          <ShimmerBlock className="h-6 w-28 rounded-v-pill" />
          <ShimmerBlock className="h-12 w-full max-w-2xl rounded-v-input" />
          <ShimmerBlock className="h-72 rounded-v-card" />
          <ShimmerBlock className="h-4 w-full rounded-v-pill" />
          <ShimmerBlock className="h-4 w-11/12 rounded-v-pill" />
          <ShimmerBlock className="h-4 w-10/12 rounded-v-pill" />
          <ShimmerBlock className="h-4 w-full rounded-v-pill" />
          <ShimmerBlock className="h-4 w-9/12 rounded-v-pill" />
        </div>
        <ShimmerBlock className="hidden h-80 rounded-v-card lg:block" />
      </div>
    </PortalPageContainer>
  )
}

/** Squelette détail offre / coffre — hero + colonne d'investissement. */
export function PortalOfferDetailSkeleton() {
  return (
    <PortalPageContainer>
      <ShimmerBlock className="mb-6 h-6 w-32 rounded-v-pill" />
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)] lg:gap-12">
        <div className="space-y-6">
          <ShimmerBlock className="aspect-[16/9] min-h-[260px] rounded-v-card" />
          <ShimmerBlock className="h-9 w-3/4 rounded-v-input" />
          <ShimmerBlock className="h-40 rounded-v-card" />
          <ShimmerBlock className="h-64 rounded-v-card" />
        </div>
        <ShimmerBlock className="h-[420px] rounded-v-card" />
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
  if (normalized === PORTAL_ROUTES.invest) {
    return <PortalInvestSkeleton />
  }
  if (normalized.startsWith(`${PORTAL_ROUTES.invest}/`)) {
    return <PortalOfferDetailSkeleton />
  }
  if (normalized === PORTAL_ROUTES.profile) {
    return <PortalProfileSkeleton />
  }
  if (normalized === PORTAL_ROUTES.academy) {
    return <PortalAcademySkeleton />
  }
  if (normalized.startsWith(`${PORTAL_ROUTES.academy}/`)) {
    return <PortalArticleSkeleton />
  }
  if (normalized === PORTAL_ROUTES.myWallets) {
    return <PortalProfileSkeleton />
  }
  if (
    normalized === PORTAL_ROUTES.cryptoWallet ||
    normalized.startsWith(`${PORTAL_ROUTES.cryptoWallet}/`)
  ) {
    return <PortalDashboardSkeleton />
  }

  return <PortalGenericSkeleton />
}
