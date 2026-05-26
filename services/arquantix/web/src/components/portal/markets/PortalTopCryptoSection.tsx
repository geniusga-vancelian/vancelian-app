'use client'

import { useMemo, useState } from 'react'

import { AppAccountSummaryList } from '@/components/design-system/app/AppAccountSummaryList'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalCryptoAsset } from '@/lib/portal/marketsTypes'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import { PORTAL_ROUTES, portalCryptoInstrumentRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type TabId = 'favorites' | 'popular' | 'gainers' | 'losers' | 'allCrypto'

export type TopCryptoTabId = TabId

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'favorites', label: 'Favorites' },
  { id: 'popular', label: 'Popular' },
  { id: 'gainers', label: 'Top Gainers' },
  { id: 'losers', label: 'Top Losers' },
  { id: 'allCrypto', label: 'All crypto' },
]

type Props = {
  popular: PortalCryptoAsset[]
  topGainers: PortalCryptoAsset[]
  topLosers: PortalCryptoAsset[]
  favorites: PortalCryptoAsset[]
  allCrypto: PortalCryptoAsset[]
  activeTab?: TopCryptoTabId
  onTabChange?: (tab: TopCryptoTabId) => void
  loading?: boolean
  allCryptoLoading?: boolean
  error?: string
  onRetry?: () => void
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

export function PortalTopCryptoSection({
  popular,
  topGainers,
  topLosers,
  favorites,
  allCrypto,
  activeTab: activeTabProp,
  onTabChange,
  loading,
  allCryptoLoading,
  error,
  onRetry,
}: Props) {
  const [internalTab, setInternalTab] = useState<TabId>('popular')
  const tab = activeTabProp ?? internalTab

  const setTab = (next: TabId) => {
    if (onTabChange) onTabChange(next)
    else setInternalTab(next)
  }

  const rows = useMemo(() => {
    if (tab === 'favorites') return favorites
    if (tab === 'gainers') return topGainers
    if (tab === 'losers') return topLosers
    if (tab === 'allCrypto') return allCrypto
    return popular
  }, [allCrypto, favorites, popular, tab, topGainers, topLosers])

  const emptyMessage =
    tab === 'favorites'
      ? 'Star an instrument on its detail page to add it to your favorites.'
      : tab === 'allCrypto'
        ? 'No crypto instruments are available.'
        : 'No assets to display.'

  const showLoading = loading || (tab === 'allCrypto' && allCryptoLoading)

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title="Top Crypto" href={PORTAL_ROUTES.markets} />

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={cn(
              'rounded-v-pill border px-3 py-1.5 font-ui text-[13px] font-medium transition-colors duration-v-fast',
              tab === item.id
                ? 'border-v-fg bg-v-fg text-white'
                : 'border-v-fg-10 bg-v-card text-v-fg-body hover:border-v-fg-20',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {showLoading ? (
        <div className="h-64 animate-pulse rounded-v-card bg-v-card" />
      ) : error ? (
        <div className="rounded-v-card border border-v-fg-10 bg-v-card p-5 text-center">
          <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="v-text-link mt-3 border-0 bg-transparent p-0 font-ui text-[13px]"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-v-card border border-v-fg-10 bg-v-card p-5 text-center">
          <p className="m-0 font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
        </div>
      ) : (
        <AppAccountSummaryList>
          {rows.map((asset) => (
            <AssetRow key={`${tab}-${asset.id}`} asset={asset} />
          ))}
        </AppAccountSummaryList>
      )}
    </section>
  )
}
