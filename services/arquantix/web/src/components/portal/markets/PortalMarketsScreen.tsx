'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalCryptoBundlesSection } from '@/components/portal/markets/PortalCryptoBundlesSection'
import { PortalMarketsNewsSection } from '@/components/portal/markets/PortalMarketsNewsSection'
import { PortalResearchSection } from '@/components/portal/markets/PortalResearchSection'
import { PortalTopCryptoSection, type TopCryptoTabId } from '@/components/portal/markets/PortalTopCryptoSection'
import { applyQuoteUpdates } from '@/lib/portal/marketsFormat'
import { Container } from '@/components/ui/Container'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import type { PortalCryptoAsset, PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import {
  getPortalCacheBootstrap,
  writePortalCache,
} from '@/lib/portal/portalClientCache'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

const MARKETS_CACHE_KEY = 'portal:markets:v2'
const ALL_CRYPTO_CACHE_KEY = 'portal:all-crypto:v2'

function initialLiveLists(payload: PortalMarketsPayload | null) {
  const allCryptoBootstrap = getPortalCacheBootstrap<PortalCryptoAsset[]>(ALL_CRYPTO_CACHE_KEY)
  return {
    livePopular: payload?.popular ?? [],
    liveGainers: payload?.topGainers ?? [],
    liveLosers: payload?.topLosers ?? [],
    liveFavorites: payload?.favorites ?? [],
    liveAllCrypto: allCryptoBootstrap.data ?? payload?.allCrypto ?? [],
  }
}

function MarketsSkeleton() {
  return (
    <PortalPageContainer>
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)] lg:gap-16">
        <div className="space-y-6">
          <div className="h-24 animate-pulse rounded-v-card bg-v-card" />
          <div className="h-72 animate-pulse rounded-v-card bg-v-card" />
          <div className="h-56 animate-pulse rounded-v-card bg-v-card" />
        </div>
        <div className="hidden h-56 animate-pulse rounded-v-card bg-v-card-warm lg:block" />
      </div>
    </PortalPageContainer>
  )
}

function symbolsForTab(
  tab: TopCryptoTabId,
  popular: PortalCryptoAsset[],
  topGainers: PortalCryptoAsset[],
  topLosers: PortalCryptoAsset[],
  favorites: PortalCryptoAsset[],
  allCrypto: PortalCryptoAsset[],
): string[] {
  const list =
    tab === 'favorites'
      ? favorites
      : tab === 'gainers'
        ? topGainers
        : tab === 'losers'
          ? topLosers
          : tab === 'allCrypto'
            ? allCrypto
            : popular
  return list.map((asset) => asset.symbol).filter(Boolean)
}

export function PortalMarketsScreen() {
  const router = useRouter()
  const marketsBootstrap = getPortalCacheBootstrap<PortalMarketsPayload>(MARKETS_CACHE_KEY)
  const initialLive = initialLiveLists(marketsBootstrap.data)
  const allCryptoBootstrap = getPortalCacheBootstrap<PortalCryptoAsset[]>(ALL_CRYPTO_CACHE_KEY)

  const { data, loading, refreshing, error, refresh } = usePortalCachedScreen<PortalMarketsPayload>({
    cacheKey: MARKETS_CACHE_KEY,
    url: '/api/portal/markets',
    ttlMs: 90_000,
    errorMessage: 'Unable to load markets.',
  })

  const [livePopular, setLivePopular] = useState(initialLive.livePopular)
  const [liveGainers, setLiveGainers] = useState(initialLive.liveGainers)
  const [liveLosers, setLiveLosers] = useState(initialLive.liveLosers)
  const [liveFavorites, setLiveFavorites] = useState(initialLive.liveFavorites)
  const [liveAllCrypto, setLiveAllCrypto] = useState(initialLive.liveAllCrypto)
  const [activeTab, setActiveTab] = useState<TopCryptoTabId>('popular')
  const [allCryptoLoading, setAllCryptoLoading] = useState(false)
  const [allCryptoLoaded, setAllCryptoLoaded] = useState(
    () => Boolean(allCryptoBootstrap.hasInitialData && (allCryptoBootstrap.data?.length ?? 0) > 0),
  )

  useEffect(() => {
    if (!data) return
    setLivePopular(data.popular)
    setLiveGainers(data.topGainers)
    setLiveLosers(data.topLosers)
    setLiveFavorites(data.favorites ?? [])
    const cachedAllCrypto = getPortalCacheBootstrap<PortalCryptoAsset[]>(ALL_CRYPTO_CACHE_KEY)
    if (!cachedAllCrypto.hasInitialData) {
      setLiveAllCrypto(data.allCrypto ?? [])
    }
  }, [data])

  const loadAllCrypto = useCallback(async () => {
    const bootstrap = getPortalCacheBootstrap<PortalCryptoAsset[]>(ALL_CRYPTO_CACHE_KEY)
    if (bootstrap.hasInitialData && bootstrap.data?.length) {
      setLiveAllCrypto(bootstrap.data)
      setAllCryptoLoaded(true)
    }

    const showSpinner = !bootstrap.hasInitialData
    if (showSpinner) setAllCryptoLoading(true)

    try {
      const res = await fetch('/api/portal/markets/all-crypto', { credentials: 'include' })
      if (res.status === 401) {
        router.replace(PORTAL_ROUTES.login)
        return
      }
      if (!res.ok) return
      const json = (await res.json()) as { items?: PortalCryptoAsset[] }
      const items = json.items ?? []
      writePortalCache(ALL_CRYPTO_CACHE_KEY, items, 120_000)
      setLiveAllCrypto(items)
      setAllCryptoLoaded(true)
    } catch {
      /* onglet All crypto reste vide */
    } finally {
      if (showSpinner) setAllCryptoLoading(false)
    }
  }, [router])

  useEffect(() => {
    if (activeTab !== 'allCrypto' || allCryptoLoaded || allCryptoLoading) return
    void loadAllCrypto()
  }, [activeTab, allCryptoLoaded, allCryptoLoading, loadAllCrypto])

  const wsSymbols = useMemo(
    () => symbolsForTab(activeTab, livePopular, liveGainers, liveLosers, liveFavorites, liveAllCrypto),
    [activeTab, livePopular, liveGainers, liveLosers, liveFavorites, liveAllCrypto],
  )

  const handleWsQuotes = useCallback(
    (updates: Parameters<typeof applyQuoteUpdates>[1]) => {
      if (activeTab === 'favorites') {
        setLiveFavorites((prev) => applyQuoteUpdates(prev, updates, 'USD'))
      } else if (activeTab === 'allCrypto') {
        setLiveAllCrypto((prev) => applyQuoteUpdates(prev, updates, 'USD'))
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

  if (loading && !data) return <MarketsSkeleton />

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
        <PortalPageIntro
          eyebrow="Markets"
          title="Crypto Markets"
          description="Live USD prices, top movers, thematic bundles, news and research."
        />

        <PortalTopCryptoSection
          popular={livePopular}
          topGainers={liveGainers}
          topLosers={liveLosers}
          favorites={liveFavorites}
          allCrypto={liveAllCrypto}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          loading={false}
          allCryptoLoading={allCryptoLoading}
          error={topCryptoError}
          onRetry={() => void refresh()}
        />

        <PortalCryptoBundlesSection bundles={data.bundles} />

        <PortalMarketsNewsSection items={data.news} />

        <PortalResearchSection items={data.research} />

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
