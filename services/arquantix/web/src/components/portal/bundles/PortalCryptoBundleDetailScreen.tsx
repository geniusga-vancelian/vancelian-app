'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'next/navigation'

import { PortalLazyBundleInvestDialog } from '@/components/portal/bundles/PortalLazyBundleInvestDialog'
import {
  PortalPanierAside,
  PortalPanierCompositionSection,
  PortalPanierExitsSection,
  PortalPanierFaqSection,
  PortalPanierHero,
  PortalPanierMetricsSection,
  PortalPanierMobileCta,
  PortalPanierOverviewSection,
  PortalPanierPerformanceSection,
  PortalPanierPerfWindowsGrid,
  PortalPanierResourcesSection,
  PortalPanierWhySection,
} from '@/components/portal/bundles/PortalPanierDetailSections'
import { PortalOfferAdvisorCard } from '@/components/portal/invest/PortalOfferDetailSections'
import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalDetailBackLink } from '@/components/portal/PortalDetailBackLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalDashboardSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { Button } from '@/components/ui/button'
import { Container } from '@/components/ui/Container'
import { parseBundleChartPoints } from '@/lib/portal/bundleProductFormat'
import type { PortalBundleProductDetailPayload } from '@/lib/portal/bundleProductTypes'
import {
  buildPortalPanierDetailView,
  PANIER_PERF_WINDOW_PERIODS,
} from '@/lib/portal/bundlePanierDetailFormat'
import type { ChartPeriodId } from '@/lib/portal/instrumentDetailFormat'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  productCode: string
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

/** Détail panier crypto — handoff Panier.html (`ofd-*` · `cfd-*` · `pnr-*`). */
export function PortalCryptoBundleDetailScreen({ productCode }: Props) {
  const searchParams = useSearchParams()
  const code = productCode.trim().toUpperCase()
  const fromInvest = searchParams?.get('back') === 'invest'
  const backHref = fromInvest ? PORTAL_ROUTES.invest : PORTAL_ROUTES.markets
  const backLabel = fromInvest ? 'Retour à Placer' : 'Retour aux marchés'

  const [data, setData] = useState<PortalBundleProductDetailPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [period, setPeriod] = useState<ChartPeriodId>('1a')
  const [chartPoints, setChartPoints] = useState<number[]>([])
  const [chartPerfPct, setChartPerfPct] = useState<number | null>(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [chartError, setChartError] = useState<string | null>(null)
  const [perf1yPct, setPerf1yPct] = useState<number | null>(null)
  const [perfWindows, setPerfWindows] = useState<Array<{ label: string; pct: number | null }>>(
    [],
  )
  const [investOpen, setInvestOpen] = useState(false)

  const loadDetail = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/portal/bundles/product/${encodeURIComponent(code)}`, {
        credentials: 'include',
        cache: 'no-store',
      })
      if (res.status === 401) {
        window.location.href = PORTAL_ROUTES.login
        return
      }
      if (!res.ok) {
        setError('Impossible de charger le panier.')
        return
      }
      setData((await res.json()) as PortalBundleProductDetailPayload)
    } catch {
      setError('Impossible de charger le panier.')
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
        setChartError('Graphique indisponible.')
        return
      }
      const json = await res.json()
      const parsed = parseBundleChartPoints(json)
      setChartPoints(parsed.historyPoints)
      setChartPerfPct(parsed.performancePct)
      if (nextPeriod === '1a') {
        setPerf1yPct(parsed.performancePct)
      }
    } catch {
      setChartError('Graphique indisponible.')
    } finally {
      setChartLoading(false)
    }
  }, [code])

  const loadPerfWindows = useCallback(async () => {
    const uniquePeriods = [...new Set(PANIER_PERF_WINDOW_PERIODS.map((w) => w.period))]
    const results = await Promise.all(
      uniquePeriods.map(async (periodId) => {
        try {
          const res = await fetch(
            `/api/portal/bundles/product/${encodeURIComponent(code)}/chart-history?period=${encodeURIComponent(periodId)}`,
            { credentials: 'include', cache: 'no-store' },
          )
          if (!res.ok) return { period: periodId, pct: null as number | null }
          const json = await res.json()
          return { period: periodId, pct: parseBundleChartPoints(json).performancePct }
        } catch {
          return { period: periodId, pct: null }
        }
      }),
    )
    const byPeriod = Object.fromEntries(results.map((r) => [r.period, r.pct]))
    setPerfWindows(
      PANIER_PERF_WINDOW_PERIODS.map((w) => ({
        label: w.label,
        pct: byPeriod[w.period] ?? null,
      })),
    )
  }, [code])

  useEffect(() => {
    void loadDetail()
  }, [loadDetail])

  useEffect(() => {
    void loadChart(period)
  }, [loadChart, period])

  useEffect(() => {
    void loadPerfWindows()
  }, [loadPerfWindows])

  const view = useMemo(
    () => (data ? buildPortalPanierDetailView(data, { perf1yPct }) : null),
    [data, perf1yPct],
  )

  const investBundle = data ? toInvestBundle(data) : null
  const investLabel = view?.isCoffre ? 'Déposer dans ce coffre' : 'Investir dans ce panier'
  const canInvest = Boolean(data?.portfolioId)

  if (loading && !data) {
    return <PortalDashboardSkeleton />
  }

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 text-center font-ui text-[15px] text-v-error">{error}</p>
        <Button type="button" onClick={() => void loadDetail()}>
          Réessayer
        </Button>
      </Container>
    )
  }

  if (!data || !view) return null

  const openInvest = () => {
    if (canInvest) setInvestOpen(true)
  }

  return (
    <PortalPageContainer className="ofd-page ofd-page--bundle">
      <PortalDetailBackLink href={backHref} label={backLabel} />

      <PortalPortfolioLayout
        main={
          <>
            <PortalPanierHero view={view} />
            {view.advisorText ? <PortalOfferAdvisorCard text={view.advisorText} /> : null}
            <PortalPanierMetricsSection view={view} />
            <PortalPanierWhySection view={view} />
            <PortalPanierOverviewSection view={view} />
            <PortalPanierCompositionSection view={view} />
            <PortalPanierPerformanceSection
              period={period}
              onPeriodChange={setPeriod}
              chartPoints={chartPoints}
              chartPerfPct={chartPerfPct}
              loading={chartLoading}
              error={chartError}
            />
            <PortalPanierPerfWindowsGrid windows={perfWindows} />
            <PortalPanierExitsSection view={view} onInvest={openInvest} />
            <PortalPanierFaqSection view={view} />
            <PortalPanierResourcesSection view={view} />
          </>
        }
        side={
          canInvest ? (
            <PortalPanierAside view={view} onInvest={openInvest} investLabel={investLabel} />
          ) : undefined
        }
      />

      {canInvest ? (
        <PortalPanierMobileCta view={view} onInvest={openInvest} investLabel={investLabel} />
      ) : null}

      {investBundle && canInvest ? (
        <PortalLazyBundleInvestDialog
          bundle={investBundle}
          open={investOpen}
          onOpenChange={setInvestOpen}
        />
      ) : null}
    </PortalPageContainer>
  )
}
