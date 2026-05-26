'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PieChart } from 'lucide-react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { AppDataList } from '@/components/design-system/app/AppDataList'
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
  return (
    <AppDataList title={title} isEmpty={rows.length === 0} emptyMessage={emptyMessage}>
      {rows.map((row) => {
        if (row.kind === 'bundle') {
          const perf = formatPerfPct(row.bundle.performancePct)
          const valueLabel = formatCryptoMoney(
            row.bundle.totalMarketValue ?? row.bundle.totalCostBasis,
            currency,
          )
          return (
            <div
              key={`bundle-${row.bundle.portfolioId}`}
              className="list__item list__item--static flex w-full items-center gap-3 opacity-70"
            >
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input bg-v-blue text-white">
                <PieChart className="h-5 w-5" strokeWidth={1.75} />
              </span>
              <div className="list__body min-w-0 flex-1">
                <div className="list__title">{row.bundle.portfolioName}</div>
                <div className="list__sub">
                  {row.bundle.assetsCount} actif{row.bundle.assetsCount === 1 ? '' : 's'}
                </div>
              </div>
              <div className="list__amt-col flex shrink-0 flex-col items-end gap-0.5">
                <span className="list__amt">{valueLabel}</span>
                {perf ? (
                  <span className={cn('list__indic', perfToneClass(row.bundle.performancePct))}>
                    {perf}
                  </span>
                ) : null}
              </div>
            </div>
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
          <PortalNavLink
            key={`position-${position.asset}`}
            href={href}
            className="list__item flex w-full items-center gap-3 no-underline"
          >
            <PortalCryptoAvatar
              ticker={position.asset}
              symbol={position.providerSymbol ?? tickerToProviderSymbol(position.asset)}
              apiLogoUrl={position.logoUrl}
              size="md"
            />
            <div className="list__body min-w-0 flex-1">
              <div className="list__title">{position.name}</div>
              <div className="list__sub">{resolvePositionSubtitle(position)}</div>
            </div>
            <div className="list__amt-col flex shrink-0 flex-col items-end gap-0.5">
              <span className="list__amt">{valueLabel}</span>
              {perf ? (
                <span className={cn('list__indic', perfToneClass(position.performance1dPct))}>
                  {perf}
                </span>
              ) : null}
              <KalaiIcon name="chevron-right" size={20} className="list__chv shrink-0" />
            </div>
          </PortalNavLink>
        )
      })}
    </AppDataList>
  )
}
