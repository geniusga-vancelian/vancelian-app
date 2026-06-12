'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalMarketsSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalCryptoBundlesSection } from '@/components/portal/markets/PortalCryptoBundlesSection'
import {
  PortalMarketsNewsSectionLazy,
  PortalMarketsSidebarLazy,
  PortalResearchSectionLazy,
} from '@/components/portal/markets/portalMarketsLazyChunks'
import { PortalMarketsWhenVisible } from '@/components/portal/markets/PortalMarketsWhenVisible'
import { PortalTopCryptoSection, type TopCryptoTabId } from '@/components/portal/markets/PortalTopCryptoSection'
import {
  PortalMarketsSectionSkeleton,
  PortalPlacerSectionSkeleton,
} from '@/components/portal/PortalRouteSkeleton'
import { applyQuoteUpdates } from '@/lib/portal/marketsFormat'
import { Container } from '@/components/ui/Container'
import type {
  PortalCryptoAsset,
  PortalMarketsBundlesPayload,
  PortalMarketsDiscoverPayload,
  PortalMarketsTopPayload,
} from '@/lib/portal/marketsTypes'
import { PORTAL_SECTION_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { usePortalProgressiveSections } from '@/lib/portal/usePortalProgressiveSections'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

function symbolsForTab(
  tab: TopCryptoTabId,
  popular: PortalCryptoAsset[],
  topGainers: PortalCryptoAsset[],
  topLosers: PortalCryptoAsset[],
  favorites: PortalCryptoAsset[],
): string[] {
  const list =
    tab === 'favorites'
      ? favorites
      : tab === 'gainers'
        ? topGainers
        : tab === 'losers'
          ? topLosers
          : popular
  return list.map((asset) => asset.symbol).filter(Boolean)
}

type MarketsSections = {
  top: PortalMarketsTopPayload
  bundles: PortalMarketsBundlesPayload
  discover: PortalMarketsDiscoverPayload
}

export function PortalMarketsScreen() {
  const { sections, refreshing, refresh } = usePortalProgressiveSections<MarketsSections>({
    top: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.marketsTop,
      url: '/api/portal/markets/top',
      ttlMs: 90_000,
      errorMessage: 'Unable to load markets.',
    },
    bundles: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.marketsBundles,
      url: '/api/portal/markets/bundles',
      ttlMs: 120_000,
    },
    discover: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.marketsDiscover,
      url: '/api/portal/markets/discover',
      ttlMs: 180_000,
    },
  })

  const top = sections.top
  const bundles = sections.bundles
  const discover = sections.discover

  const [livePopular, setLivePopular] = useState<PortalCryptoAsset[]>([])
  const [liveGainers, setLiveGainers] = useState<PortalCryptoAsset[]>([])
  const [liveLosers, setLiveLosers] = useState<PortalCryptoAsset[]>([])
  const [liveFavorites, setLiveFavorites] = useState<PortalCryptoAsset[]>([])
  const [activeTab, setActiveTab] = useState<TopCryptoTabId>('gainers')

  useEffect(() => {
    if (!top.data) return
    setLivePopular(top.data.popular)
    setLiveGainers(top.data.topGainers)
    setLiveLosers(top.data.topLosers)
    setLiveFavorites(top.data.favorites ?? [])
  }, [top.data])

  const wsSymbols = useMemo(
    () => symbolsForTab(activeTab, livePopular, liveGainers, liveLosers, liveFavorites),
    [activeTab, livePopular, liveGainers, liveLosers, liveFavorites],
  )

  const handleWsQuotes = useCallback(
    (updates: Parameters<typeof applyQuoteUpdates>[1]) => {
      if (activeTab === 'favorites') {
        setLiveFavorites((prev) => applyQuoteUpdates(prev, updates, 'USD'))
      } else if (activeTab === 'popular') {
        setLivePopular((prev) => applyQuoteUpdates(prev, updates, 'USD'))
      } else if (activeTab === 'gainers') {
        setLiveGainers((prev) => applyQuoteUpdates(prev, updates, 'USD'))
      } else {
        setLiveLosers((prev) => applyQuoteUpdates(prev, updates, 'USD'))
      }
    },
    [activeTab],
  )

  useMarketDataQuotesWs(
    wsSymbols,
    handleWsQuotes,
    Boolean(top.data) && wsSymbols.length > 0,
    top.data?.marketDataPublicBaseUrl,
  )

  if (top.loading && !top.data) return <PortalMarketsSkeleton />

  if (top.error && !top.data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{top.error}</p>
        <button
          type="button"
          onClick={() => void refresh()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Réessayer
        </button>
      </Container>
    )
  }

  const topCryptoError =
    livePopular.length === 0 && liveGainers.length === 0 && liveLosers.length === 0
      ? 'Les données de marché sont temporairement indisponibles.'
      : undefined

  const bundlesPending = bundles.loading && !bundles.data
  const bundleList = bundles.data?.bundles ?? []
  const discoverPending = discover.loading && !discover.data
  const anyPartial = Boolean(
    top.data?.partial || bundles.data?.partial || discover.data?.partial,
  )

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <div className="mk-grid">
            <PortalReveal index={0}>
              <PortalTopCryptoSection
                popular={livePopular}
                topGainers={liveGainers}
                topLosers={liveLosers}
                favorites={liveFavorites}
                activeTab={activeTab}
                onTabChange={setActiveTab}
                loading={false}
                error={topCryptoError}
                onRetry={() => void refresh()}
              />
            </PortalReveal>

            {bundlesPending ? (
              <PortalReveal index={1}>
                <PortalPlacerSectionSkeleton />
              </PortalReveal>
            ) : bundleList.length > 0 ? (
              <PortalReveal index={1}>
                <PortalCryptoBundlesSection bundles={bundleList} />
              </PortalReveal>
            ) : null}

            <PortalReveal index={2}>
              <PortalMarketsWhenVisible fallback={<PortalMarketsSectionSkeleton />}>
                {discoverPending ? (
                  <PortalMarketsSectionSkeleton />
                ) : (
                  <PortalMarketsNewsSectionLazy
                    items={discover.data?.news ?? []}
                    title="Actualités"
                  />
                )}
              </PortalMarketsWhenVisible>
            </PortalReveal>

            <PortalReveal index={3}>
              <PortalMarketsWhenVisible fallback={<PortalMarketsSectionSkeleton variant="compact" />}>
                {discoverPending ? (
                  <PortalMarketsSectionSkeleton variant="compact" />
                ) : (
                  <PortalResearchSectionLazy
                    items={discover.data?.research ?? []}
                    title="Analyses"
                    maxItems={2}
                  />
                )}
              </PortalMarketsWhenVisible>
            </PortalReveal>

            {anyPartial ? (
              <p className="m-0 font-ui text-[12px] text-v-fg-muted">
                Certaines sections n&apos;ont pas pu être chargées entièrement.
              </p>
            ) : null}

            <button
              type="button"
              disabled={refreshing}
              onClick={() => void refresh()}
              className={cn(
                'v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px]',
                refreshing && 'opacity-50',
              )}
            >
              {refreshing ? 'Actualisation…' : 'Actualiser'}
            </button>
          </div>
        }
        side={
          <PortalMarketsWhenVisible fallback={<PortalMarketsSectionSkeleton variant="sidebar" />}>
            <PortalMarketsSidebarLazy />
          </PortalMarketsWhenVisible>
        }
      />
    </PortalPageContainer>
  )
}
