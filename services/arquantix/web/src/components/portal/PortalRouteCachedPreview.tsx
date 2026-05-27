'use client'

import { PortalDashboardView } from '@/components/portal/dashboard/PortalDashboardView'
import { PortalExclusiveOffersSection } from '@/components/portal/invest/PortalExclusiveOffersSection'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalTopCryptoSection } from '@/components/portal/markets/PortalTopCryptoSection'
import { PortalCryptoBundlesSection } from '@/components/portal/markets/PortalCryptoBundlesSection'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalRouteSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoWalletPositionsCard } from '@/components/portal/wallet/PortalCryptoWalletPositionsCard'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import {
  buildUnifiedWalletRows,
  formatCryptoMoney,
  resolveHubCountLabel,
  resolveHubTotalValue,
} from '@/lib/portal/cryptoWalletFormat'
import {
  readPortalRouteCachedPayload,
  type PortalRouteCachedPayload,
} from '@/lib/portal/portalRouteCachePreview'
import { cn } from '@/lib/utils'

type Props = {
  route: string
  className?: string
}

function ProfileCachedPreview({
  data,
}: {
  data: Extract<PortalRouteCachedPayload, { kind: 'profile' }>['data']
}) {
  const profile = data.profile
  const email = profile?.email?.trim() || 'Profile'
  const initials =
    profile?.initials?.trim().slice(0, 2).toUpperCase() ||
    profile?.personal?.first_name?.trim().charAt(0).toUpperCase() ||
    '?'

  return (
    <PortalPageContainer>
      <div className="mx-auto flex max-w-2xl flex-col gap-8">
        <section className="flex items-center gap-4">
          <span className="inline-flex h-14 w-14 items-center justify-center rounded-v-pill bg-v-fg font-ui text-[18px] font-semibold text-white">
            {initials}
          </span>
          <div>
            <AppEyebrow>Account</AppEyebrow>
            <h1 className="m-0 font-ui text-[22px] font-semibold text-v-fg">{email}</h1>
          </div>
        </section>
      </div>
    </PortalPageContainer>
  )
}

function CryptoWalletCachedPreview({
  data,
}: {
  data: Extract<PortalRouteCachedPayload, { kind: 'crypto-wallet' }>['data']
}) {
  const rows = buildUnifiedWalletRows(data.positions.positions, data.bundles, data.currency)
  const totalLabel = formatCryptoMoney(
    resolveHubTotalValue(data.positions, data.bundles, data.currency),
    data.currency,
  )
  const countLabel = resolveHubCountLabel(data.positions, data.bundles, {
    privyOnly: data.source === 'privy',
  })

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <section className="overflow-hidden rounded-v-card border border-[#0D1B2A]/20 bg-[#0D1B2A] p-4 text-white shadow-v-subtle sm:p-5">
          <AppEyebrow className="text-white/70">Wallet</AppEyebrow>
          <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight">Crypto</h1>
          <p className="mt-2 mb-0 font-ui text-[28px] font-bold leading-none sm:text-[32px]">
            {totalLabel}
          </p>
          <p className="mt-2 mb-0 font-ui text-[13px] text-white/70">{countLabel}</p>
          <div className="mt-4 border-t border-white/10 pt-4">
            <PortalPerformanceChart values={data.historyPoints} tone="dark" height={88} />
          </div>
        </section>
        <PortalCryptoWalletPositionsCard rows={rows} currency={data.currency} />
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}

/** Affiche le contenu en cache pendant la transition Next.js (stale-while-navigate). */
export function PortalRouteCachedPreview({ route, className }: Props) {
  const payload = readPortalRouteCachedPayload(route)

  if (!payload) {
    return <PortalRouteSkeleton route={route} />
  }

  return (
    <div
      className={cn('flex flex-1 flex-col', className)}
      aria-busy="true"
      aria-live="polite"
      data-portal-cache-preview="true"
    >
      {payload.kind === 'dashboard' ? (
        <PortalDashboardView data={payload.data} showRefreshLink={false} />
      ) : null}

      {payload.kind === 'markets' ? (
        <PortalPageContainer>
          <PortalDashboardLayout>
            <PortalReveal index={0}>
              <PortalPageIntro eyebrow="Markets" title="Markets" />
            </PortalReveal>
            <PortalTopCryptoSection
              popular={payload.data.popular}
              topGainers={payload.data.topGainers}
              topLosers={payload.data.topLosers}
              favorites={payload.data.favorites}
            />
            <PortalCryptoBundlesSection bundles={payload.data.bundles} />
          </PortalDashboardLayout>
        </PortalPageContainer>
      ) : null}

      {payload.kind === 'invest' ? (
        <PortalPageContainer>
          <PortalDashboardLayout>
            <PortalReveal index={0}>
              <PortalPageIntro
                eyebrow="Investing"
                title="Invest"
                description="Explore DeFi vaults and exclusive offers to build your portfolio."
              />
            </PortalReveal>
            <PortalExclusiveOffersSection offers={payload.data.offers} title="Exclusive offers" />
          </PortalDashboardLayout>
        </PortalPageContainer>
      ) : null}

      {payload.kind === 'profile' ? <ProfileCachedPreview data={payload.data} /> : null}

      {payload.kind === 'crypto-wallet' ? (
        <CryptoWalletCachedPreview data={payload.data} />
      ) : null}
    </div>
  )
}
