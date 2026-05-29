'use client'

import { Fragment } from 'react'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalMarketsSparkline } from '@/components/portal/markets/PortalMarketsSparkline'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import type { PortalCryptoAsset } from '@/lib/portal/marketsTypes'
import { portalCryptoInstrumentRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  assets: PortalCryptoAsset[]
  emptyMessage?: string
}

function formatMarketsChangePct(changePct: number): string {
  const sign = changePct >= 0 ? '+ ' : '− '
  return `${sign}${formatChangePctIndicator(changePct)}`
}

function MarketAssetRow({ asset, rank }: { asset: PortalCryptoAsset; rank: number }) {
  const positive = asset.changePct >= 0

  return (
    <PortalNavLink
      href={portalCryptoInstrumentRoute(asset.ticker)}
      className="mk-row no-underline"
    >
      <span className="mk-row__rank">{String(rank).padStart(2, '0')}</span>
      <span className="mk-row__ic" aria-hidden>
        <PortalCryptoAvatar
          ticker={asset.ticker}
          symbol={asset.symbol}
          apiLogoUrl={asset.logoUrl}
          size="md"
          className="!h-9 !w-9"
        />
      </span>
      <span className="mk-row__body">
        <span className="mk-row__name">{asset.name}</span>
        <span className="mk-row__sym">{asset.ticker}</span>
      </span>
      <span className="mk-row__spark">
        <PortalMarketsSparkline
          ticker={asset.ticker}
          changePct={asset.changePct}
          sparkline24h={asset.sparkline24h ?? []}
          positive={positive}
        />
      </span>
      <span className="mk-row__nums">
        <span className="mk-row__price">{asset.priceLabel}</span>
        <span className={cn('mk-row__chg', positive ? 'mk-row__chg--up' : 'mk-row__chg--down')}>
          {formatMarketsChangePct(asset.changePct)}
        </span>
      </span>
      <KalaiIcon name="chevron-right" size={16} className="mk-row__chv" aria-hidden />
    </PortalNavLink>
  )
}

/** Liste marchés — handoff Marches.html `.mk-row` dans `.v-card--list`. */
export function PortalMarketsAssetList({
  assets,
  emptyMessage = 'Aucun actif à afficher.',
}: Props) {
  if (assets.length === 0) {
    return (
      <div className="v-card v-card--list px-6 py-10 text-center">
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="v-card v-card--list">
      {assets.map((asset, index) => (
        <Fragment key={asset.id}>
          <MarketAssetRow asset={asset} rank={index + 1} />
          {index < assets.length - 1 ? <hr className="hr-thin" /> : null}
        </Fragment>
      ))}
    </div>
  )
}
