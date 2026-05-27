'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalMarketsSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalCryptoBundlesSection } from '@/components/portal/markets/PortalCryptoBundlesSection'
import { PortalMarketsNewsSection } from '@/components/portal/markets/PortalMarketsNewsSection'
import { PortalResearchSection } from '@/components/portal/markets/PortalResearchSection'
import { PortalTopCryptoSection, type TopCryptoTabId } from '@/components/portal/markets/PortalTopCryptoSection'
import { applyQuoteUpdates } from '@/lib/portal/marketsFormat'
import { Container } from '@/components/ui/Container'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

const MARKETS_CACHE_KEY = 'portal:markets:v2'

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
  const [activeTab, setActiveTab] = useState<TopCryptoTabId>('popular')

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

  if (loading && !data) return <PortalMarketsSkeleton />

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
        <button
          type="button"
          onClick={() => void refresh()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Retry
        </button>
      </Container>
    )
  }

  if (!data) return null

  const topCryptoError =
    livePopular.length === 0 && liveGainers.length === 0 && liveLosers.length === 0
      ? 'Market data is temporarily unavailable.'
      : undefined

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <PortalPageIntro
            eyebrow="Markets"
            title="Crypto Markets"
            description="Live USD prices, top movers, thematic bundles, news and research."
          />
        </PortalReveal>

        <PortalReveal index={1}>
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

        <PortalReveal index={2}>
          <PortalCryptoBundlesSection bundles={data.bundles} />
        </PortalReveal>

        <PortalReveal index={3}>
          <PortalMarketsNewsSection items={data.news} />
        </PortalReveal>

        <PortalReveal index={4}>
          <PortalResearchSection items={data.research} maxItems={2} />
        </PortalReveal>

        {data.partial ? (
          <p className="m-0 font-ui text-[12px] text-v-fg-muted">
            Some market sections could not be loaded completely.
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
          {refreshing ? 'Refreshing…' : 'Refresh markets'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
