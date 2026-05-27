'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { useRouter } from 'next/navigation'
import { ArrowDown, ArrowLeft, ArrowUp, Star } from 'lucide-react'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalInstrumentChartModule } from '@/components/portal/markets/PortalInstrumentChartModule'
import { PortalSolanaWalletSection } from '@/components/portal/markets/PortalSolanaWalletSection'
import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalMarketsNewsSection } from '@/components/portal/markets/PortalMarketsNewsSection'
import { PortalResearchSection } from '@/components/portal/markets/PortalResearchSection'
import { Button } from '@/components/ui/button'
import {
  type ChartPeriodId,
  formatChangePct,
  formatCryptoPrice,
  formatPeriodCaption,
  formatUsdAbsChange,
  parseInstrumentCandles,
  periodPerformanceFromCandles,
  tickerToProviderSymbol,
} from '@/lib/portal/instrumentDetailFormat'
import type { PortalInstrumentDetailPayload } from '@/lib/portal/instrumentDetailTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

type Props = {
  ticker: string
}

type PortalFavoriteRow = {
  id: string
  entity_type: string
  entity_id: string
}

export function PortalInstrumentDetailScreen({ ticker }: Props) {
  const router = useRouter()
  const [data, setData] = useState<PortalInstrumentDetailPayload | null>(null)
  const [livePriceUsd, setLivePriceUsd] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState<ChartPeriodId>('1j')
  const [displayPeriod, setDisplayPeriod] = useState<ChartPeriodId>('1j')
  const [candles, setCandles] = useState<ReturnType<typeof parseInstrumentCandles>>([])
  const [candlesLoading, setCandlesLoading] = useState(false)
  const [candlesError, setCandlesError] = useState<string | null>(null)
  const [isFavorite, setIsFavorite] = useState(false)
  const [favoriteId, setFavoriteId] = useState<string | null>(null)
  const [favoriteBusy, setFavoriteBusy] = useState(false)

  const symbol = useMemo(
    () => (data?.symbol ? data.symbol : tickerToProviderSymbol(ticker)),
    [data?.symbol, ticker],
  )

  const favoriteEntityId = useMemo(() => tickerToProviderSymbol(ticker), [ticker])

  const loadDetail = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/portal/instruments/${encodeURIComponent(ticker)}`, {
        credentials: 'include',
        cache: 'no-store',
      })
      if (res.status === 401) {
        router.replace(PORTAL_ROUTES.login)
        return
      }
      if (!res.ok) {
        setError('Unable to load instrument.')
        return
      }
      const json = (await res.json()) as PortalInstrumentDetailPayload
      setData(json)
      setLivePriceUsd(json.priceUsd > 0 ? json.priceUsd : null)
    } catch {
      setError('Unable to load instrument.')
    } finally {
      setLoading(false)
    }
  }, [router, ticker])

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
          setCandlesError('Chart data is temporarily unavailable.')
          return
        }
        const json = (await res.json()) as { candles?: unknown }
        setCandles(parseInstrumentCandles(json.candles))
        setDisplayPeriod(nextPeriod)
      } catch {
        setCandlesError('Chart data is temporarily unavailable.')
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
  }, [loadFavoriteStatus])

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
            Back to Markets
          </PortalNavLink>
        </div>
      </PortalPageContainer>
    )
  }

  if (!data) return null

  const perfPositive = (periodPerf?.absUsd ?? 0) >= 0
  const isSolInstrument = ticker.trim().toUpperCase() === 'SOL'

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalNavLink
          href={PORTAL_ROUTES.markets}
          className="inline-flex w-fit items-center gap-2 font-ui text-[14px] font-medium text-v-fg-body no-underline transition-colors hover:text-v-fg"
        >
          <ArrowLeft className="h-4 w-4" />
          Markets
        </PortalNavLink>

        <section className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-fg-05">
          <div className="flex flex-col gap-5 p-5 sm:p-6">
            <AppEyebrow>Crypto</AppEyebrow>

            <div className="flex items-center gap-3">
              <PortalCryptoAvatar
                ticker={data.ticker}
                symbol={data.symbol}
                apiLogoUrl={data.logoUrl}
                size="md"
              />
              <h1 className="m-0 flex-1 font-ui text-[22px] font-semibold tracking-v-tight text-v-fg sm:text-[26px]">
                {data.name}
              </h1>
              <button
                type="button"
                onClick={() => void toggleFavorite()}
                disabled={favoriteBusy}
                aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                className={cn(
                  'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-v-fg-10 bg-v-card transition-colors duration-v-fast hover:border-v-fg-20 disabled:opacity-50',
                )}
              >
                <Star
                  className={cn(
                    'h-5 w-5',
                    isFavorite ? 'fill-[#FFB800] text-[#FFB800]' : 'text-v-fg-muted',
                  )}
                />
              </button>
            </div>

            <p className="m-0 font-ui text-[28px] font-bold leading-none tracking-v-tight text-v-fg sm:text-[32px]">
              {priceLabel}
            </p>

            {periodPerf ? (
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    'rounded-v-pill px-2.5 py-1 font-ui text-[12px] font-semibold',
                    perfPositive ? 'bg-v-green-bg text-v-green' : 'bg-v-error-bg text-v-error',
                  )}
                >
                  {formatUsdAbsChange(periodPerf.absUsd)}
                </span>
                <span
                  className={cn(
                    'font-ui text-[13px] font-semibold',
                    perfPositive ? 'text-v-green' : 'text-v-error',
                  )}
                >
                  {formatChangePct(periodPerf.pct)}
                </span>
                <span className="font-ui text-[13px] text-v-fg-muted">
                  {formatPeriodCaption(displayPeriod)}
                </span>
              </div>
            ) : null}

            <PortalInstrumentChartModule
              candles={candles}
              period={period}
              onPeriodChange={setPeriod}
              loading={candlesLoading}
              error={candlesError}
              onRetry={() => void loadCandles(period)}
            />

            <div className="flex flex-wrap gap-2 border-t border-v-fg-10 pt-5">
              <Button type="button" className="gap-1.5" disabled>
                <ArrowUp className="h-4 w-4" />
                Buy
              </Button>
              <Button type="button" variant="outline" className="gap-1.5" disabled>
                <ArrowDown className="h-4 w-4" />
                Sell
              </Button>
            </div>
          </div>
        </section>

        {isSolInstrument ? <PortalSolanaWalletSection /> : null}

        <PortalMarketsNewsSection items={data.news} showFilters={false} />

        <PortalResearchSection items={data.research} />
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
