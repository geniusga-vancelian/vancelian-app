'use client'

import { useMemo, useState } from 'react'

import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalCryptoAssetList } from '@/components/portal/markets/PortalCryptoAssetList'
import type { PortalCryptoAsset } from '@/lib/portal/marketsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type TabId = 'favorites' | 'popular' | 'gainers' | 'losers'

export type TopCryptoTabId = TabId

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'favorites', label: 'Favorites' },
  { id: 'popular', label: 'Popular' },
  { id: 'gainers', label: 'Top Gainers' },
  { id: 'losers', label: 'Top Losers' },
]

type Props = {
  popular: PortalCryptoAsset[]
  topGainers: PortalCryptoAsset[]
  topLosers: PortalCryptoAsset[]
  favorites: PortalCryptoAsset[]
  /** Liste affichée telle quelle (page « All crypto »). */
  assets?: PortalCryptoAsset[]
  activeTab?: TopCryptoTabId
  onTabChange?: (tab: TopCryptoTabId) => void
  showTabs?: boolean
  showBrowseLink?: boolean
  title?: string
  browseHref?: string
  browseLabel?: string
  loading?: boolean
  error?: string
  onRetry?: () => void
  emptyMessage?: string
}

export function PortalTopCryptoSection({
  popular,
  topGainers,
  topLosers,
  favorites,
  assets: assetsProp,
  activeTab: activeTabProp,
  onTabChange,
  showTabs = true,
  showBrowseLink = true,
  title = 'Top Crypto',
  browseHref = PORTAL_ROUTES.marketsAllCrypto,
  browseLabel = 'Browse all Crypto',
  loading,
  error,
  onRetry,
  emptyMessage,
}: Props) {
  const [internalTab, setInternalTab] = useState<TabId>('popular')
  const tab = activeTabProp ?? internalTab

  const setTab = (next: TabId) => {
    if (onTabChange) onTabChange(next)
    else setInternalTab(next)
  }

  const rows = useMemo(() => {
    if (assetsProp) return assetsProp
    if (tab === 'favorites') return favorites
    if (tab === 'gainers') return topGainers
    if (tab === 'losers') return topLosers
    return popular
  }, [assetsProp, favorites, popular, tab, topGainers, topLosers])

  const resolvedEmptyMessage =
    emptyMessage ??
    (tab === 'favorites'
      ? 'Star an instrument on its detail page to add it to your favorites.'
      : 'No assets to display.')

  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader
        title={title}
        moreHref={showBrowseLink ? browseHref : undefined}
        moreLabel={browseLabel}
      />

      {showTabs ? (
        <div className="nx__filters">
          <div className="seg" role="tablist">
            {TABS.map((item) => {
              const active = tab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={cn('seg__item', active && 'is-on')}
                  onClick={() => setTab(item.id)}
                >
                  {item.label}
                </button>
              )
            })}
          </div>
        </div>
      ) : null}

      {loading ? (
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
      ) : (
        <PortalCryptoAssetList assets={rows} emptyMessage={resolvedEmptyMessage} />
      )}
    </section>
  )
}
