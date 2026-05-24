'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { ChevronRight, PieChart } from 'lucide-react'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import {
  formatCryptoMoney,
  formatPerfPct,
  perfToneClass,
  resolvePositionSubtitle,
} from '@/lib/portal/cryptoWalletFormat'
import type { PortalCryptoWalletRow } from '@/lib/portal/cryptoWalletTypes'
import { tickerToProviderSymbol } from '@/lib/portal/instrumentDetailFormat'
import { portalCryptoWalletAssetRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  rows: PortalCryptoWalletRow[]
  currency: string
  title?: string
  emptyMessage?: string
}

export function PortalCryptoWalletPositionsCard({
  rows,
  currency,
  title = 'Positions',
  emptyMessage = 'Aucune position crypto pour le moment',
}: Props) {
  if (rows.length === 0) {
    return (
      <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card p-8 text-center shadow-v-subtle">
        <p className="m-0 font-ui text-[15px] text-v-fg-muted">{emptyMessage}</p>
      </article>
    )
  }

  return (
    <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
      <div className="border-b border-v-fg-10 px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">{title}</h2>
      </div>
      <ul className="m-0 list-none p-0">
        {rows.map((row) => {
          if (row.kind === 'bundle') {
            const perf = formatPerfPct(row.bundle.performancePct)
            const valueLabel = formatCryptoMoney(
              row.bundle.totalMarketValue ?? row.bundle.totalCostBasis,
              currency,
            )
            return (
              <li key={`bundle-${row.bundle.portfolioId}`}>
                <div className="flex w-full items-center gap-3 px-4 py-3.5 text-left opacity-70">
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input bg-[#6366F1] text-white">
                    <PieChart className="h-5 w-5" strokeWidth={1.75} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-ui text-[15px] font-semibold text-v-fg">
                      {row.bundle.portfolioName}
                    </span>
                    <span className="mt-0.5 block truncate font-ui text-[13px] text-v-fg-muted">
                      {row.bundle.assetsCount} actif{row.bundle.assetsCount === 1 ? '' : 's'}
                    </span>
                  </span>
                  <span className="flex shrink-0 flex-col items-end gap-0.5">
                    <span className="font-ui text-[15px] font-semibold tabular-nums text-v-fg">
                      {valueLabel}
                    </span>
                    {perf ? (
                      <span className={cn('font-ui text-[12px] tabular-nums', perfToneClass(row.bundle.performancePct))}>
                        {perf}
                      </span>
                    ) : null}
                  </span>
                </div>
              </li>
            )
          }

          const { position } = row
          const perf = formatPerfPct(position.performance1dPct)
          const href = portalCryptoWalletAssetRoute(position.asset)

          return (
            <li key={`position-${position.asset}`}>
              <PortalNavLink
                href={href}
                className="flex w-full items-center gap-3 px-4 py-3.5 text-left no-underline transition-colors duration-v-fast hover:bg-v-card-hover"
              >
                <PortalCryptoAvatar
                  ticker={position.asset}
                  symbol={position.providerSymbol ?? tickerToProviderSymbol(position.asset)}
                  apiLogoUrl={position.logoUrl}
                  size="md"
                />
                <span className="min-w-0 flex-1">
                  <span className="block font-ui text-[15px] font-semibold text-v-fg">
                    {position.name}
                  </span>
                  <span className="mt-0.5 block truncate font-ui text-[13px] text-v-fg-muted">
                    {resolvePositionSubtitle(position)}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <span className="flex flex-col items-end gap-0.5">
                    <span className="font-ui text-[15px] font-semibold tabular-nums text-v-fg">
                      {formatCryptoMoney(
                        currency === 'USD'
                          ? position.estimatedValueUsd ?? position.estimatedValueEur
                          : position.estimatedValueEur ?? position.estimatedValueUsd,
                        currency,
                      )}
                    </span>
                    {perf ? (
                      <span
                        className={cn(
                          'font-ui text-[12px] tabular-nums',
                          perfToneClass(position.performance1dPct),
                        )}
                      >
                        {perf}
                      </span>
                    ) : null}
                  </span>
                  <ChevronRight className="h-4 w-4 text-v-fg-muted" aria-hidden />
                </span>
              </PortalNavLink>
            </li>
          )
        })}
      </ul>
    </article>
  )
}
