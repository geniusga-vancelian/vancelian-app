'use client'

import { PieChart } from 'lucide-react'
import {
  AppAccountSummaryList,
} from '@/components/design-system/app/AppAccountSummaryList'
import {
  AppAccountSummaryRow,
  type AppAccountIndicatorTone,
} from '@/components/design-system/app/AppAccountSummaryRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import {
  formatCryptoMoney,
  formatPerfPct,
  resolvePositionSubtitle,
} from '@/lib/portal/cryptoWalletFormat'
import type { PortalCryptoWalletRow } from '@/lib/portal/cryptoWalletTypes'
import { cryptoPositionHeaderTitle, tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import {
  portalCryptoWalletAssetRoute,
  portalCryptoWalletBundleRoute,
} from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  rows: PortalCryptoWalletRow[]
  currency: string
  title?: string
  emptyMessage?: string
}

function perfIndicatorTone(pct: number | undefined): AppAccountIndicatorTone | undefined {
  if (pct == null || Number.isNaN(pct)) return undefined
  if (pct > 0.005) return 'up'
  if (pct < -0.005) return 'dn'
  return 'plus'
}

export function PortalCryptoWalletPositionsCard({
  rows,
  currency,
  title = 'Positions',
  emptyMessage = 'No crypto positions yet',
}: Props) {
  if (rows.length === 0) {
    return (
      <section className="flex w-full flex-col gap-3">
        <AppSectionHeader title={title} />
        <p className="m-0 rounded-v-card border border-v-fg-10 bg-v-card px-6 py-10 text-center font-ui text-[15px] text-v-fg-muted">
          {emptyMessage}
        </p>
      </section>
    )
  }

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} />
      <AppAccountSummaryList>
        {rows.map((row) => {
          if (row.kind === 'bundle') {
            const perf = formatPerfPct(row.bundle.performancePct)
            const valueLabel = formatCryptoMoney(
              row.bundle.totalMarketValue ?? row.bundle.totalCostBasis,
              currency,
            )
            return (
              <AppAccountSummaryRow
                key={`bundle-${row.bundle.portfolioId}`}
                href={portalCryptoWalletBundleRoute(row.bundle.portfolioId)}
                LinkComponent={PortalNavLink}
                leading={
                  <span className="inline-flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full bg-v-blue text-white">
                    <PieChart className="h-6 w-6" strokeWidth={1.75} aria-hidden />
                  </span>
                }
                title={row.bundle.portfolioName}
                subtitle={`${row.bundle.assetsCount} asset${row.bundle.assetsCount === 1 ? '' : 's'}`}
                amount={valueLabel}
                indicator={perf ?? undefined}
                indicatorTone={perfIndicatorTone(row.bundle.performancePct)}
                showChevron={false}
              />
            )
          }

          const { position } = row
          const perf = formatPerfPct(position.performance1dPct)
          const href = portalCryptoWalletAssetRoute(position.asset)
          const valueLabel = formatCryptoMoney(
            currency === 'USD'
              ? position.estimatedValueUsd ?? position.estimatedValueEur
              : position.estimatedValueEur ?? position.estimatedValueUsd,
            currency,
          )

          return (
            <AppAccountSummaryRow
              key={`position-${position.asset}`}
              href={href}
              LinkComponent={PortalNavLink}
              leading={
                <PortalCryptoAvatar
                  ticker={position.asset}
                  symbol={position.providerSymbol ?? tickerToProviderSymbol(position.asset)}
                  apiLogoUrl={position.logoUrl}
                  size="lg"
                />
              }
              title={cryptoPositionHeaderTitle(position.asset, position.name)}
              subtitle={resolvePositionSubtitle(position)}
              amount={valueLabel}
              indicator={perf ?? undefined}
              indicatorTone={perfIndicatorTone(position.performance1dPct)}
              showChevron={false}
            />
          )
        })}
      </AppAccountSummaryList>
    </section>
  )
}
