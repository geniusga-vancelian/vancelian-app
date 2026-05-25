'use client'

import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalInvestSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalPageIntro, PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { PortalExclusiveOffersSection } from '@/components/portal/invest/PortalExclusiveOffersSection'
import { PortalEarnVaultSection } from '@/components/portal/invest/PortalEarnVaultSection'
import { PortalLedgityVaultSection } from '@/components/portal/invest/PortalLedgityVaultSection'
import { Container } from '@/components/ui/Container'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { isPortalChainDeFiEnabled } from '@/lib/portal/portalChainFilter'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { cn } from '@/lib/utils'

const INVEST_CACHE_KEY = 'portal:invest:v2'

export function PortalInvestScreen() {
  const { chain } = usePortalChainContext()
  const showDeFiVaults = isPortalChainDeFiEnabled(chain)
  const { data, loading, refreshing, error, refresh } = usePortalCachedScreen<PortalInvestPayload>({
    cacheKey: INVEST_CACHE_KEY,
    url: '/api/portal/invest?locale=en',
    ttlMs: 120_000,
    errorMessage: 'Unable to load invest products.',
  })

  if (loading && !data) return <PortalInvestSkeleton />

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
        <PortalReveal index={0}>
          <PortalPageIntro
            eyebrow="Investing"
            title="Invest"
            description="Explore DeFi vaults and exclusive offers to build your portfolio."
          />
        </PortalReveal>

        {showDeFiVaults ? (
          <PortalReveal index={1}>
            <section id="defi-vaults" className="flex scroll-mt-24 flex-col gap-8">
              <PortalSectionHeading title="DeFi vaults" />
              <PortalEarnVaultSection embedded />
              <PortalLedgityVaultSection embedded />
            </section>
          </PortalReveal>
        ) : null}

        <PortalReveal index={2}>
          <PortalExclusiveOffersSection offers={data.offers} title="Exclusive offers" />
        </PortalReveal>

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
