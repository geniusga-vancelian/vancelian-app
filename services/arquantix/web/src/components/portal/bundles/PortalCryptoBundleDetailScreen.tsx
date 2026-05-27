'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Star } from 'lucide-react'

import { AppButton } from '@/components/design-system/app/AppButton'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { buildProductBasketStackFromTickers } from '@/components/design-system/app/AppProductBasketCard'
import { PortalBundleInvestDialog } from '@/components/portal/bundles/PortalBundleInvestDialog'
import { PortalBundleProductModules } from '@/components/portal/bundles/PortalBundleProductModules'
import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import {
  findPerformanceChartModule,
  parseBundleChartPoints,
} from '@/lib/portal/bundleProductFormat'
import type { PortalBundleProductDetailPayload } from '@/lib/portal/bundleProductTypes'
import {
  CHART_PERIOD_OPTIONS,
  type ChartPeriodId,
  formatPeriodCaption,
} from '@/lib/portal/instrumentDetailFormat'
import { formatChangePctIndicator } from '@/lib/portal/marketsFormat'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  productCode: string
}

type PortalFavoriteRow = {
  id: string
  entity_type: string
  entity_id: string
}

function resolveBundleHeroImage(payload: PortalBundleProductDetailPayload): string | null {
  if (payload.headerMediaUrl?.trim()) return payload.headerMediaUrl.trim()
  if (payload.detailMediaUrl?.trim()) return payload.detailMediaUrl.trim()
  const code = payload.productCode.toLowerCase()
  if (code.includes('flex')) return '/app-ds/assets/photos/coffre-flex.png'
  if (code.includes('avenir') || code.includes('future')) {
    return '/app-ds/assets/photos/coffre-avenir.png'
  }
  return '/app-ds/assets/photos/panier-crypto.png'
}

function toInvestBundle(payload: PortalBundleProductDetailPayload): PortalCryptoBundle {
  return {
    id: payload.productId ?? payload.productCode,
    code: payload.productCode,
    title: payload.title,
    description: payload.subtitle,
    imageUrl: payload.headerMediaUrl,
    performance1d: null,
    riskLabel: payload.riskLabel,
    portfolioId: payload.portfolioId,
    productId: payload.productId,
    entryAssetDefault: payload.entryAssetDefault,
    entryAssetsAllowed: payload.entryAssetsAllowed,
    allocationTickers: payload.allocations.map((a) => a.assetSymbol),
    sortOrder: 999,
  }
}

export function PortalCryptoBundleDetailScreen({ productCode }: Props) {
  const code = productCode.trim().toUpperCase()
  const [data, setData] = useState<PortalBundleProductDetailPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState<ChartPeriodId>('1a')
  const [chartPoints, setChartPoints] = useState<number[]>([])
  const [chartPerfPct, setChartPerfPct] = useState<number | null>(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [chartError, setChartError] = useState<string | null>(null)
  const [investOpen, setInvestOpen] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false)
  const [favoriteId, setFavoriteId] = useState<string | null>(null)
  const [favoriteBusy, setFavoriteBusy] = useState(false)

  const favoriteEntityId = data?.productId ?? data?.productCode ?? code

  const loadDetail = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(
        `/api/portal/bundles/product/${encodeURIComponent(code)}`,
        { credentials: 'include', cache: 'no-store' },
      )
      if (res.status === 401) {
        window.location.href = PORTAL_ROUTES.login
        return
      }
      if (!res.ok) {
        setError('Unable to load bundle.')
        return
      }
      setData((await res.json()) as PortalBundleProductDetailPayload)
    } catch {
      setError('Unable to load bundle.')
    } finally {
      setLoading(false)
    }
  }, [code])

  const loadChart = useCallback(async (nextPeriod: ChartPeriodId) => {
    setChartLoading(true)
    setChartError(null)
    try {
      const res = await fetch(
        `/api/portal/bundles/product/${encodeURIComponent(code)}/chart-history?period=${encodeURIComponent(nextPeriod)}`,
        { credentials: 'include', cache: 'no-store' },
      )
      if (!res.ok) {
        setChartError('Chart unavailable.')
        return
      }
      const json = await res.json()
      const parsed = parseBundleChartPoints(json)
      setChartPoints(parsed.historyPoints)
      setChartPerfPct(parsed.performancePct)
    } catch {
      setChartError('Chart unavailable.')
    } finally {
      setChartLoading(false)
    }
  }, [code])

  const loadFavoriteStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/portal/favorites?entity_type=bundle', {
        credentials: 'include',
        cache: 'no-store',
      })
      if (!res.ok) return
      const favs = (await res.json()) as PortalFavoriteRow[]
      if (!Array.isArray(favs)) return
      const match = favs.find(
        (f) => f.entity_type === 'bundle' && f.entity_id === favoriteEntityId,
      )
      setIsFavorite(Boolean(match))
      setFavoriteId(match?.id ?? null)
    } catch {
      /* ignore */
    }
  }, [favoriteEntityId])

  useEffect(() => {
    void loadDetail()
  }, [loadDetail])

  useEffect(() => {
    void loadFavoriteStatus()
  }, [loadFavoriteStatus])

  useEffect(() => {
    void loadChart(period)
  }, [loadChart, period])

  const perfChartModule = useMemo(
    () => (data ? findPerformanceChartModule(data.modules) : undefined),
    [data],
  )
  const perfChartTitle =
    (typeof perfChartModule?.content.title === 'string'
      ? perfChartModule.content.title.trim()
      : '') || 'Performance'

  const stack = useMemo(() => {
    if (!data) return { assets: [], moreCount: undefined }
    const tickers =
      data.allocations.length > 0
        ? data.allocations.map((a) => a.assetSymbol)
        : data.entryAssetsAllowed
    return buildProductBasketStackFromTickers(tickers)
  }, [data])

  const perfLabel = useMemo(() => {
    if (chartPerfPct == null) return '—'
    const formatted = formatChangePctIndicator(chartPerfPct)
    return `${chartPerfPct >= 0 ? '+' : '−'}${formatted}`
  }, [chartPerfPct])

  const toggleFavorite = async () => {
    if (!data || favoriteBusy) return
    setFavoriteBusy(true)
    try {
      if (isFavorite && favoriteId) {
        const res = await fetch(`/api/portal/favorites/${encodeURIComponent(favoriteId)}`, {
          method: 'DELETE',
          credentials: 'include',
        })
        if (res.ok) {
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
          entity_type: 'bundle',
          entity_id: favoriteEntityId,
        }),
      })
      if (res.ok) {
        const row = (await res.json()) as PortalFavoriteRow
        setIsFavorite(true)
        setFavoriteId(row.id)
      }
    } finally {
      setFavoriteBusy(false)
    }
  }

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void loadDetail()}>
          Retry
        </Button>
      </Container>
    )
  }

  if (!data) return null

  const investBundle = toInvestBundle(data)
  const positive = chartPerfPct == null || chartPerfPct >= 0

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
              <PortalNavLink
                href={PORTAL_ROUTES.markets}
                className="inline-flex w-fit items-center gap-1.5 font-ui text-[13px] text-v-fg-muted no-underline transition-colors hover:text-v-fg"
              >
                <ArrowLeft className="h-4 w-4" />
                Markets
              </PortalNavLink>
              <button
                type="button"
                disabled={favoriteBusy}
                onClick={() => void toggleFavorite()}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-v-fg-10 bg-white text-v-fg transition-colors hover:bg-v-fg-05 disabled:opacity-50"
                aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
              >
                <Star
                  className={cn('h-5 w-5', isFavorite && 'fill-[#FFB800] text-[#FFB800]')}
                />
              </button>
            </div>

            <div className="overflow-hidden rounded-v-card border border-v-fg-10 bg-[#0D1B2A] text-white shadow-v-subtle">
              <div className="relative min-h-[200px] p-5 sm:p-6">
                {resolveBundleHeroImage(data) ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={resolveBundleHeroImage(data)!}
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover opacity-35"
                  />
                ) : null}
                <div className="relative z-[1] flex flex-col gap-4">
                  <AppEyebrow className="text-white/80">Crypto Bundle</AppEyebrow>
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <h1 className="m-0 font-ui text-[clamp(28px,4vw,40px)] font-semibold leading-tight">
                        {data.title}
                      </h1>
                      {data.subtitle ? (
                        <p className="mt-2 mb-0 max-w-2xl font-ui text-[14px] leading-relaxed text-white/75">
                          {data.subtitle}
                        </p>
                      ) : null}
                    </div>
                    {stack.assets.length > 0 ? (
                      <div className="prod__stack shrink-0" aria-hidden>
                        {stack.assets.map((asset, index) => (
                          <span key={`${asset.src}-${index}`} className="a">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={asset.src} alt={asset.alt ?? ''} />
                          </span>
                        ))}
                        {stack.moreCount ? (
                          <span className="a a--more">+{stack.moreCount}</span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>

                  <div className="flex flex-wrap items-baseline gap-3">
                    <span
                      className={cn(
                        'font-ui text-[28px] font-bold leading-none sm:text-[32px]',
                        positive ? 'text-v-green' : 'text-v-error',
                      )}
                    >
                      {perfLabel}
                    </span>
                    <span className="font-ui text-[13px] text-white/70">
                      {formatPeriodCaption(period)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="border-t border-white/10 bg-[#0D1B2A] px-3 py-4 sm:px-5">
                <p className="m-0 mb-3 font-ui text-[13px] font-medium text-white/80">
                  {perfChartTitle}
                </p>
                <div className="flex flex-wrap gap-2">
                  {CHART_PERIOD_OPTIONS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setPeriod(item.id)}
                      className={cn(
                        'rounded-v-pill border px-3 py-1.5 font-ui text-[12px] font-medium transition-colors duration-v-fast',
                        period === item.id
                          ? 'border-white bg-white text-[#0D1B2A]'
                          : 'border-white/20 bg-transparent text-white/80 hover:bg-white/10',
                      )}
                    >
                      {item.chip}
                    </button>
                  ))}
                </div>
                <div className="mt-4 min-h-[120px]">
                  {chartLoading && chartPoints.length === 0 ? (
                    <div className="flex h-[100px] items-center justify-center">
                      <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                    </div>
                  ) : chartError && chartPoints.length === 0 ? (
                    <p className="m-0 py-8 text-center font-ui text-[13px] text-white/60">
                      {chartError}
                    </p>
                  ) : chartPoints.length >= 2 ? (
                    <PortalPerformanceChart
                      values={chartPoints}
                      height={100}
                      tone="dark"
                      className={positive ? 'text-v-green' : 'text-v-error'}
                    />
                  ) : (
                    <p className="m-0 py-8 text-center font-ui text-[13px] text-white/60">
                      No chart data for this period.
                    </p>
                  )}
                </div>
              </div>

              {data.portfolioId ? (
                <div className="flex justify-center border-t border-white/10 px-5 py-4">
                  <AppButton type="button" size="lg" onClick={() => setInvestOpen(true)}>
                    Invest
                  </AppButton>
                </div>
              ) : null}
            </div>
          </div>
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalBundleProductModules modules={data.modules} />
        </PortalReveal>

        {data.portfolioId ? (
          <PortalBundleInvestDialog
            bundle={investBundle}
            open={investOpen}
            onOpenChange={setInvestOpen}
          />
        ) : null}
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
