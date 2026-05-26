'use client'

import { AppAccountSummaryList } from '@/components/design-system/app/AppAccountSummaryList'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalCryptoAsset } from '@/lib/portal/marketsTypes'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import { portalCryptoInstrumentRoute } from '@/lib/portal/portalRouting'

type Props = {
  assets: PortalCryptoAsset[]
  emptyMessage?: string
}

function AssetRow({ asset }: { asset: PortalCryptoAsset }) {
  const positive = asset.changePct >= 0

  return (
    <AppAccountSummaryRow
      href={portalCryptoInstrumentRoute(asset.ticker)}
      LinkComponent={PortalNavLink}
      leading={
        <PortalCryptoAvatar
          ticker={asset.ticker}
          symbol={asset.symbol}
          apiLogoUrl={asset.logoUrl}
          size="lg"
          className="!h-[52px] !w-[52px]"
        />
      }
      title={asset.name}
      subtitle={asset.ticker}
      amount={asset.priceLabel}
      indicator={formatChangePctIndicator(asset.changePct)}
      indicatorTone={positive ? 'up' : 'dn'}
    />
  )
}

/** Liste crypto DS — lignes `AppAccountSummaryRow` (preview/67). */
export function PortalCryptoAssetList({
  assets,
  emptyMessage = 'No assets to display.',
}: Props) {
  if (assets.length === 0) {
    return (
      <div className="rounded-v-card border border-v-fg-10 bg-v-card p-5 text-center">
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <AppAccountSummaryList>
      {assets.map((asset) => (
        <AssetRow key={asset.id} asset={asset} />
      ))}
    </AppAccountSummaryList>
  )
}
