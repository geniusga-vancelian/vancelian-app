'use client'

import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageIntro, PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { PortalExclusiveOffersSection } from '@/components/portal/invest/PortalExclusiveOffersSection'
import { PortalInvestProductAccess } from '@/components/portal/invest/PortalInvestProductAccess'
import { Container } from '@/components/ui/Container'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

const INVEST_CACHE_KEY = 'portal:invest:v2'

function InvestSkeleton() {
  return (
    <PortalPageContainer>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16">
        <div className="space-y-6">
          <div className="h-40 animate-pulse rounded-v-card bg-v-card" />
          <div className="h-72 animate-pulse rounded-v-card bg-v-card" />
          <div className="h-80 animate-pulse rounded-v-card bg-v-card" />
        </div>
        <div className="hidden h-56 animate-pulse rounded-v-card bg-v-card-warm lg:block" />
      </div>
    </PortalPageContainer>
  )
}

export function PortalInvestScreen() {
  const { data, loading, refreshing, error, refresh } = usePortalCachedScreen<PortalInvestPayload>({
    cacheKey: INVEST_CACHE_KEY,
    url: '/api/portal/invest?locale=fr',
    ttlMs: 120_000,
    errorMessage: 'Unable to load invest products.',
  })

  if (loading && !data) return <InvestSkeleton />

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
        <button
          type="button"
          onClick={() => void refresh()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Retry
        </button>
      </Container>
    )
  }

  if (!data) return null

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-end">
          <PortalPageIntro
            eyebrow="Invest"
            title={data.heroTitle}
            description={data.heroSubtitle}
          />
          {data.heroImageUrl ? (
            <div className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={data.heroImageUrl} alt="" className="aspect-[4/3] w-full object-cover" />
            </div>
          ) : null}
        </div>

        <section className="flex flex-col gap-4">
          <PortalSectionHeading title="Explore opportunities" />
          <PortalInvestProductAccess />
        </section>

        <PortalExclusiveOffersSection offers={data.offers} />

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void refresh()}
          className={cn(
            'v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px]',
            refreshing && 'opacity-50',
          )}
        >
          {refreshing ? 'Refreshing…' : 'Refresh offers'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
