'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalInstrumentAboutSection } from '@/components/portal/markets/PortalInstrumentAboutSection'
import { PortalInstrumentChartModule } from '@/components/portal/markets/PortalInstrumentChartModule'
import { PortalInstrumentCtaBar } from '@/components/portal/markets/PortalInstrumentCtaBar'
import { PortalInstrumentExtendedStats } from '@/components/portal/markets/PortalInstrumentExtendedStats'
import { PortalInstrumentHeader } from '@/components/portal/markets/PortalInstrumentHeader'
import { PortalInstrumentSidebar } from '@/components/portal/markets/PortalInstrumentSidebar'
import { PortalMarketsNewsSection } from '@/components/portal/markets/PortalMarketsNewsSection'
import { PortalSolanaWalletSection } from '@/components/portal/markets/PortalSolanaWalletSection'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import type { PortalChain } from '@/config/portalChains'
import {
  type ChartPeriodId,
  buildInstrumentExtendedStats,
  buildInstrumentSidebarStats,
  formatPeriodCaption,
  parseInstrumentCandles,
  periodPerformanceFromCandles,
  tickerToProviderSymbol,
} from '@/lib/portal/instrumentDetailFormat'
import type { PortalInstrumentDetailPayload } from '@/lib/portal/instrumentDetailTypes'
import { formatCryptoPrice } from '@/lib/portal/marketsFormat'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { PORTAL_ROUTES, portalSwapBuyRoute, portalSwapSellRoute } from '@/lib/portal/portalRouting'
import { isPortalSwapTradeAsset } from '@/lib/portal/swapFlowTypes'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { useRouter } from 'next/navigation'

type Props = {
  ticker: string
}

type PortalFavoriteRow = {
  id: string
  entity_type: string
  entity_id: string
}

const MIN_TRADE_VALUE_USD = 1

function resolveSwapChainForAsset(asset: string, portalChain: PortalChain): string | undefined {
  if (asset === 'CBBTC' || asset === 'CBETH') return 'base'
  if (portalChain === 'solana') return undefined
  return portalChain
}

/** Fiche instrument marché — handoff Asset.html (`ast-*` · `portal-placer-grid`). */
export function PortalInstrumentDetailScreen({ ticker }: Props) {
  const router = useRouter()
  const { chain } = usePortalChainContext()
  const normalizedTicker = ticker.trim().toUpperCase()

  const [data, setData] = useState<PortalInstrumentDetailPayload | null>(null)
  const [livePriceUsd, setLivePriceUsd] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState<ChartPeriodId>('1a')
  const [displayPeriod, setDisplayPeriod] = useState<ChartPeriodId>('1a')
  const [candles, setCandles] = useState<ReturnType<typeof parseInstrumentCandles>>([])
  const [candlesLoading, setCandlesLoading] = useState(false)
  const [candlesError, setCandlesError] = useState<string | null>(null)
  const [isFavorite, setIsFavorite] = useState(false)
  const [favoriteId, setFavoriteId] = useState<string | null>(null)
  const [favoriteBusy, setFavoriteBusy] = useState(false)
  const [hasPosition, setHasPosition] = useState(false)

  const symbol = useMemo(
    () => (data?.symbol ? data.symbol : tickerToProviderSymbol(normalizedTicker)),
    [data?.symbol, normalizedTicker],
  )

  const favoriteEntityId = useMemo(() => tickerToProviderSymbol(normalizedTicker), [normalizedTicker])

  const loadDetail = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/portal/instruments/${encodeURIComponent(normalizedTicker)}`, {
        credentials: 'include',
        cache: 'no-store',
      })
      if (res.status === 401) {
        router.replace(PORTAL_ROUTES.login)
        return
      }
      if (!res.ok) {
        setError("Impossible de charger l'instrument.")
        return
      }
      const json = (await res.json()) as PortalInstrumentDetailPayload
      setData(json)
      setLivePriceUsd(json.priceUsd > 0 ? json.priceUsd : null)
    } catch {
      setError("Impossible de charger l'instrument.")
    } finally {
      setLoading(false)
    }
  }, [normalizedTicker, router])

  const loadFavoriteStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/portal/favorites?entity_type=instrument', {
        credentials: 'include',
        cache: 'no-store',
      })
      if (!res.ok) return
      const favs = (await res.json()) as PortalFavoriteRow[]
      if (!Array.isArray(favs)) return
      const match = favs.find(
        (f) =>
          f.entity_type === 'instrument' &&
          f.entity_id?.trim().toUpperCase() === favoriteEntityId,
      )
      setIsFavorite(Boolean(match))
      setFavoriteId(match?.id ?? null)
    } catch {
      // ignore
    }
  }, [favoriteEntityId])

  const loadPositionHint = useCallback(async () => {
    try {
      const res = await fetch(`/api/portal/crypto-wallet/${encodeURIComponent(normalizedTicker)}`, {
        credentials: 'include',
        cache: 'no-store',
      })
      if (!res.ok) return
      const json = (await res.json()) as { detail?: { volume?: string } }
      const qty = Number.parseFloat(String(json.detail?.volume ?? '').replace(',', '.')) || 0
      setHasPosition(qty > 0)
    } catch {
      // ignore
    }
  }, [normalizedTicker])

  const toggleFavorite = useCallback(async () => {
    if (favoriteBusy) return
    setFavoriteBusy(true)
    try {
      if (isFavorite && favoriteId) {
        const res = await fetch(`/api/portal/favorites/${encodeURIComponent(favoriteId)}`, {
          method: 'DELETE',
          credentials: 'include',
        })
        if (res.ok || res.status === 204) {
          setIsFavorite(false)
          setFavoriteId(null)
        }
        return
      }

      const res = await fetch('/api/portal/favorites', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_type: 'instrument',
          entity_id: favoriteEntityId,
        }),
      })
      if (!res.ok) return
      const created = (await res.json()) as PortalFavoriteRow
      if (created?.id) {
        setIsFavorite(true)
        setFavoriteId(created.id)
      }
    } finally {
      setFavoriteBusy(false)
    }
  }, [favoriteBusy, favoriteEntityId, favoriteId, isFavorite])

  const loadCandles = useCallback(
    async (nextPeriod: ChartPeriodId) => {
      setCandlesLoading(true)
      setCandlesError(null)
      try {
        const res = await fetch(
          `/api/market-data/chart-history?symbol=${encodeURIComponent(symbol)}&period=${encodeURIComponent(nextPeriod)}`,
          { cache: 'no-store' },
        )
        if (!res.ok) {
          setCandlesError('Données graphiques temporairement indisponibles.')
          return
        }
        const json = (await res.json()) as { candles?: unknown }
        setCandles(parseInstrumentCandles(json.candles))
        setDisplayPeriod(nextPeriod)
      } catch {
        setCandlesError('Données graphiques temporairement indisponibles.')
      } finally {
        setCandlesLoading(false)
      }
    },
    [symbol],
  )

  useEffect(() => {
    void loadDetail()
  }, [loadDetail])

  useEffect(() => {
    void loadFavoriteStatus()
    void loadPositionHint()
  }, [loadFavoriteStatus, loadPositionHint])

  useEffect(() => {
    if (!symbol) return
    void loadCandles(period)
  }, [loadCandles, period, symbol])

  const handleWsQuotes = useCallback(
    (updates: Array<{ symbol: string; price: number }>) => {
      const update = updates.find((u) => u.symbol.toUpperCase() === symbol.toUpperCase())
      if (update && update.price > 0) setLivePriceUsd(update.price)
    },
    [symbol],
  )

  useMarketDataQuotesWs([symbol], handleWsQuotes, Boolean(data), data?.marketDataPublicBaseUrl)

  const priceUsd = livePriceUsd ?? data?.priceUsd ?? 0
  const priceLabel = priceUsd > 0 ? formatCryptoPrice(priceUsd, 'USD') : (data?.priceLabel ?? '—')

  const periodPerf = useMemo(
    () => periodPerformanceFromCandles(candles, priceUsd > 0 ? priceUsd : null),
    [candles, priceUsd],
  )

  const sidebarStats = useMemo(
    () =>
      buildInstrumentSidebarStats({
        priceLabel,
        change24hPct: data?.change24hPct ?? 0,
        change24hAbs: data?.change24hAbs ?? null,
      }),
    [data?.change24hAbs, data?.change24hPct, priceLabel],
  )

  const extendedStats = useMemo(
    () =>
      buildInstrumentExtendedStats({
        priceLabel,
        change24hPct: data?.change24hPct ?? 0,
        change24hAbs: data?.change24hAbs ?? null,
        periodPerf,
        periodLabel: formatPeriodCaption(displayPeriod),
      }),
    [data?.change24hAbs, data?.change24hPct, displayPeriod, periodPerf, priceLabel],
  )

  const swapChainKey = resolveSwapChainForAsset(normalizedTicker, chain)
  const canTrade = priceUsd > MIN_TRADE_VALUE_USD && isPortalSwapTradeAsset(normalizedTicker)
  const buyHref = canTrade && swapChainKey ? portalSwapBuyRoute(normalizedTicker, swapChainKey) : undefined
  const sellHref =
    canTrade && swapChainKey && hasPosition
      ? portalSwapSellRoute(normalizedTicker, swapChainKey)
      : undefined

  if (loading && !data) {
    return (
      <PortalPageContainer>
        <div className="h-96 animate-pulse rounded-v-card bg-v-card" />
      </PortalPageContainer>
    )
  }

  if (error && !data) {
    return (
      <PortalPageContainer>
        <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4 text-center">
          <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
          <PortalNavLink href={PORTAL_ROUTES.markets} className="v-text-link font-ui text-[14px]">
            Retour aux marchés
          </PortalNavLink>
        </div>
      </PortalPageContainer>
    )
  }

  if (!data) return null

  const isSolInstrument = normalizedTicker === 'SOL'

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <div className="ast-page">
            <PortalDetailBackLink href={PORTAL_ROUTES.markets} label="Retour aux marchés" />

            <PortalInstrumentHeader
              ticker={data.ticker}
              symbol={data.symbol}
              name={data.name}
              logoUrl={data.logoUrl}
              priceLabel={priceLabel}
              change24hPct={data.change24hPct}
              isFavorite={isFavorite}
              favoriteBusy={favoriteBusy}
              onToggleFavorite={() => void toggleFavorite()}
            />

            <PortalInstrumentChartModule
              candles={candles}
              period={period}
              onPeriodChange={setPeriod}
              loading={candlesLoading}
              error={candlesError}
              onRetry={() => void loadCandles(period)}
              periodPerf={periodPerf}
              priceUsd={priceUsd}
            />

            <PortalInstrumentExtendedStats stats={extendedStats} />

            <PortalInstrumentAboutSection name={data.name} ticker={data.ticker} />

            {isSolInstrument ? <PortalSolanaWalletSection /> : null}

            <PortalMarketsNewsSection
              items={data.news}
              title="Actualités liées"
              showFilters={false}
            />

            <PortalInstrumentCtaBar buyHref={buyHref} sellHref={sellHref} canSell={hasPosition} />
          </div>
        }
        side={
          <PortalInstrumentSidebar
            ticker={data.ticker}
            priceUsd={priceUsd}
            sidebarStats={sidebarStats}
            buyHref={buyHref}
            sellHref={sellHref}
          />
        }
      />
    </PortalPageContainer>
  )
}
