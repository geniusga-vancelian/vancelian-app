'use client'

import { PieChart } from 'lucide-react'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
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
import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  rows: PortalCryptoWalletRow[]
  currency: string
  title?: string
  emptyMessage?: string
  footerHint?: string
}

function perfDailyLabel(pct: number | undefined): { label: string; positive: boolean } | null {
  const formatted = formatPerfPct(pct)
  if (!formatted) return null
  const positive = pct == null || pct >= -0.005
  return { label: `${formatted} / jour`, positive }
}

export function PortalCryptoWalletPositionsCard({
  rows,
  currency,
  title = 'Mes positions',
  emptyMessage = 'No crypto positions yet',
  footerHint,
}: Props) {
  if (rows.length === 0) {
    return (
      <section className="flex w-full flex-col gap-3">
        <AppSectionHeader title={title} size="sm" />
        <p className="m-0 rounded-v-card border border-v-fg-10 bg-v-card px-6 py-10 text-center font-ui text-[15px] text-v-fg-muted">
          {emptyMessage}
        </p>
      </section>
    )
  }

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} size="sm" />
      <div className="v-card v-card--list wallet-positions">
        {rows.map((row) => {
            if (row.kind === 'bundle') {
              const perf = perfDailyLabel(row.bundle.performancePct)
              const valueLabel = formatCryptoMoney(
                row.bundle.totalMarketValue ?? row.bundle.totalCostBasis,
                currency,
              )
              return (
                <AppAccountSummaryRow
                  key={`bundle-${row.bundle.portfolioId}`}
                  href={portalCryptoWalletBundleRoute(row.bundle.portfolioId)}
                  LinkComponent={PortalNavLink}
                  showChevron
                  leading={
                    <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-v-fg text-white">
                      <PieChart className="h-6 w-6" strokeWidth={1.75} aria-hidden />
                    </span>
                  }
                  title={row.bundle.portfolioName}
                  subtitle={`${row.bundle.assetsCount} actif${row.bundle.assetsCount === 1 ? '' : 's'}`}
                  amount={valueLabel}
                  dailyLabel={perf?.label}
                  dailyPositive={perf?.positive ?? true}
                />
              )
            }

            const { position } = row
            const perf = perfDailyLabel(position.performance1dPct)
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
                showChevron
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
                dailyLabel={perf?.label}
                dailyPositive={perf?.positive ?? true}
              />
            )
          })}
        {footerHint ? (
          <div className="wallet-positions__foot">
            <KalaiIcon name="info" size={16} className="shrink-0 text-v-terracotta" aria-hidden />
            <span>{footerHint}</span>
          </div>
        ) : null}
      </div>
    </section>
  )
}
