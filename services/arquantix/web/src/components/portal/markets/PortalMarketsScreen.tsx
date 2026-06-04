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
import { PortalMarketsSectionSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { applyQuoteUpdates } from '@/lib/portal/marketsFormat'
import { Container } from '@/components/ui/Container'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { PORTAL_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { shouldShowMarketsFullSkeleton } from '@/lib/portal/portalMarketsLazySections'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

const MARKETS_CACHE_KEY = PORTAL_CACHE_KEYS.markets

function symbolsForTab(
  tab: TopCryptoTabId,
  popular: PortalMarketsPayload['popular'],
  topGainers: PortalMarketsPayload['topGainers'],
  topLosers: PortalMarketsPayload['topLosers'],
  favorites: PortalMarketsPayload['favorites'],
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

export function PortalMarketsScreen() {
  const { data, loading, refreshing, error, refresh } = usePortalCachedScreen<PortalMarketsPayload>({
    cacheKey: MARKETS_CACHE_KEY,
    url: '/api/portal/markets',
    ttlMs: 90_000,
    errorMessage: 'Unable to load markets.',
  })

  const [livePopular, setLivePopular] = useState<PortalMarketsPayload['popular']>([])
  const [liveGainers, setLiveGainers] = useState<PortalMarketsPayload['topGainers']>([])
  const [liveLosers, setLiveLosers] = useState<PortalMarketsPayload['topLosers']>([])
  const [liveFavorites, setLiveFavorites] = useState<PortalMarketsPayload['favorites']>([])
  const [activeTab, setActiveTab] = useState<TopCryptoTabId>('gainers')

  useEffect(() => {
    if (!data) return
    setLivePopular(data.popular)
    setLiveGainers(data.topGainers)
    setLiveLosers(data.topLosers)
    setLiveFavorites(data.favorites ?? [])
  }, [data])

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
    Boolean(data) && wsSymbols.length > 0,
    data?.marketDataPublicBaseUrl,
  )

  if (shouldShowMarketsFullSkeleton(loading, data)) return <PortalMarketsSkeleton />

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
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

  if (!data) return null

  const topCryptoError =
    livePopular.length === 0 && liveGainers.length === 0 && liveLosers.length === 0
      ? 'Les données de marché sont temporairement indisponibles.'
      : undefined

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

            {data.bundles.length > 0 ? (
              <PortalReveal index={1}>
                <PortalCryptoBundlesSection bundles={data.bundles} />
              </PortalReveal>
            ) : null}

            <PortalReveal index={data.bundles.length > 0 ? 2 : 1}>
              <PortalMarketsWhenVisible fallback={<PortalMarketsSectionSkeleton />}>
                <PortalMarketsNewsSectionLazy items={data.news} title="Actualités" />
              </PortalMarketsWhenVisible>
            </PortalReveal>

            <PortalReveal index={data.bundles.length > 0 ? 3 : 2}>
              <PortalMarketsWhenVisible fallback={<PortalMarketsSectionSkeleton variant="compact" />}>
                <PortalResearchSectionLazy
                  items={data.research}
                  title="Analyses"
                  maxItems={2}
                />
              </PortalMarketsWhenVisible>
            </PortalReveal>

            {data.partial ? (
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
