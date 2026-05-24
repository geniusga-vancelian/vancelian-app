'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import type {
  PortalDashboardCorePayload,
  PortalDashboardPayload,
  PortalDashboardPortfolioPayload,
} from '@/lib/portal/dashboardTypes'
import {
  DASHBOARD_CORE_API_URL,
  DASHBOARD_CORE_CACHE_KEY,
  DASHBOARD_CORE_TTL_MS,
  DASHBOARD_PORTFOLIO_API_URL,
  DASHBOARD_PORTFOLIO_CACHE_KEY,
  DASHBOARD_PORTFOLIO_TTL_MS,
  getPortalDashboardBootstrapFromCache,
  resolvePortfolioCurrencyFromCore,
  syncPortalDashboardCompositeCache,
} from '@/lib/portal/dashboardCache'
import { mergePortalDashboardPayload } from '@/lib/portal/dashboardMerge'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { PortalFetchError, revalidatePortalCache } from '@/lib/portal/portalClientCache'

export type UsePortalDashboardProgressiveResult = {
  data: PortalDashboardPayload | null
  loading: boolean
  portfolioLoading: boolean
  refreshing: boolean
  error: string
  refresh: () => Promise<void>
}

function scheduleIdleRevalidate(run: () => void): void {
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(run, { timeout: 2500 })
  } else {
    window.setTimeout(run, 120)
  }
}

export function usePortalDashboardProgressive(): UsePortalDashboardProgressiveResult {
  const router = useRouter()
  const bootstrapRef = useRef(getPortalDashboardBootstrapFromCache())

  const [core, setCore] = useState<PortalDashboardCorePayload | null>(() => bootstrapRef.current.core.data)
  const [portfolio, setPortfolio] = useState<PortalDashboardPortfolioPayload | null>(
    () => bootstrapRef.current.portfolio.data,
  )
  const [loading, setLoading] = useState(() => !bootstrapRef.current.core.hasInitialData)
  const [portfolioLoading, setPortfolioLoading] = useState(
    () => !bootstrapRef.current.portfolio.hasInitialData,
  )
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const coreRef = useRef(core)
  coreRef.current = core
  const portfolioRef = useRef(portfolio)
  portfolioRef.current = portfolio

  const syncComposite = useCallback(
    (
      nextCore: PortalDashboardCorePayload | null,
      nextPortfolio: PortalDashboardPortfolioPayload | null,
    ) => {
      syncPortalDashboardCompositeCache(nextCore, nextPortfolio)
    },
    [],
  )

  const loadCore = useCallback(
    async (isManualRefresh: boolean) => {
      const hasDisplayed = coreRef.current !== null
      if (!hasDisplayed && !isManualRefresh) setLoading(true)
      try {
        const json = await revalidatePortalCache<PortalDashboardCorePayload>(
          DASHBOARD_CORE_CACHE_KEY,
          DASHBOARD_CORE_API_URL,
          DASHBOARD_CORE_TTL_MS,
        )
        setCore(json)
        syncComposite(json, portfolioRef.current)
        setError('')
        return json
      } catch (err) {
        if (err instanceof PortalFetchError && err.status === 401) {
          router.replace(PORTAL_ROUTES.login)
          return null
        }
        if (!hasDisplayed) {
          setError('Unable to load your dashboard.')
        }
        return null
      } finally {
        setLoading(false)
      }
    },
    [router, syncComposite],
  )

  const loadPortfolio = useCallback(
    async (currencyHint?: string) => {
      const hasDisplayed = portfolioRef.current !== null
      if (!hasDisplayed) setPortfolioLoading(true)
      try {
        const query = currencyHint ? `?currency=${encodeURIComponent(currencyHint)}` : ''
        const json = await revalidatePortalCache<PortalDashboardPortfolioPayload>(
          DASHBOARD_PORTFOLIO_CACHE_KEY,
          `${DASHBOARD_PORTFOLIO_API_URL}${query}`,
          DASHBOARD_PORTFOLIO_TTL_MS,
        )
        setPortfolio(json)
        syncComposite(coreRef.current, json)
      } catch (err) {
        if (err instanceof PortalFetchError && err.status === 401) {
          router.replace(PORTAL_ROUTES.login)
        }
      } finally {
        setPortfolioLoading(false)
      }
    },
    [router, syncComposite],
  )

  useEffect(() => {
    const bootstrap = bootstrapRef.current
    let cancelled = false

    const runCore = () => {
      if (cancelled) return
      void loadCore(false)
    }
    const runPortfolio = () => {
      if (cancelled) return
      const currency = resolvePortfolioCurrencyFromCore(coreRef.current)
      void loadPortfolio(currency || undefined)
    }

    if (bootstrap.core.isFresh && bootstrap.core.data) {
      scheduleIdleRevalidate(runCore)
    } else {
      runCore()
    }

    if (bootstrap.portfolio.isFresh && bootstrap.portfolio.data) {
      scheduleIdleRevalidate(runPortfolio)
    } else {
      runPortfolio()
    }

    return () => {
      cancelled = true
    }
  }, [loadCore, loadPortfolio])

  const data = useMemo(
    () => mergePortalDashboardPayload(core, portfolio),
    [core, portfolio],
  )

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const nextCore = await loadCore(true)
      await loadPortfolio(resolvePortfolioCurrencyFromCore(nextCore))
    } finally {
      setRefreshing(false)
    }
  }, [loadCore, loadPortfolio])

  return { data, loading, portfolioLoading, refreshing, error, refresh }
}
