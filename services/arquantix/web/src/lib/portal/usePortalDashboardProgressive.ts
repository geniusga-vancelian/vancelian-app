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
  resolvePortfolioCurrencyFromCore,
  syncPortalDashboardCompositeCache,
} from '@/lib/portal/dashboardCache'
import { mergePortalDashboardPayload } from '@/lib/portal/dashboardMerge'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import { appendPortalScopeQuery, buildPortalScopeCacheSuffix } from '@/lib/portal/portalScopeQuery'
import { usePortalScopeRevision } from '@/lib/portal/portalScopeReload'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  getPortalCacheBootstrap,
  PortalFetchError,
  revalidatePortalCache,
} from '@/lib/portal/portalClientCache'

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
  const { chain } = usePortalChainContext()
  const { walletScope, walletScopeId } = usePortalWalletScopeContext()
  const scopeRevision = usePortalScopeRevision()

  const scopeSuffix = buildPortalScopeCacheSuffix(chain, walletScopeId)
  const portfolioCacheKey = `${DASHBOARD_PORTFOLIO_CACHE_KEY}:${scopeSuffix}`

  const prevScopeKeyRef = useRef(`${scopeSuffix}:${scopeRevision}`)

  const [core, setCore] = useState<PortalDashboardCorePayload | null>(
    () => getPortalCacheBootstrap<PortalDashboardCorePayload>(DASHBOARD_CORE_CACHE_KEY).data,
  )
  const [portfolio, setPortfolio] = useState<PortalDashboardPortfolioPayload | null>(
    () => getPortalCacheBootstrap<PortalDashboardPortfolioPayload>(portfolioCacheKey).data,
  )
  const [loading, setLoading] = useState(
    () => !getPortalCacheBootstrap<PortalDashboardCorePayload>(DASHBOARD_CORE_CACHE_KEY).hasInitialData,
  )
  const [portfolioLoading, setPortfolioLoading] = useState(
    () => !getPortalCacheBootstrap<PortalDashboardPortfolioPayload>(portfolioCacheKey).hasInitialData,
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
    async (currencyHint?: string, isManualRefresh = false) => {
      const hasDisplayed = portfolioRef.current !== null
      if (!hasDisplayed && !isManualRefresh) setPortfolioLoading(true)
      try {
        const baseUrl = currencyHint
          ? `${DASHBOARD_PORTFOLIO_API_URL}?currency=${encodeURIComponent(currencyHint)}`
          : DASHBOARD_PORTFOLIO_API_URL
        const scopedUrl = appendPortalScopeQuery(baseUrl, chain, walletScope)
        const json = await revalidatePortalCache<PortalDashboardPortfolioPayload>(
          portfolioCacheKey,
          scopedUrl,
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
    [chain, portfolioCacheKey, router, syncComposite, walletScope],
  )

  useEffect(() => {
    const scopeKey = `${scopeSuffix}:${scopeRevision}`
    const scopeChanged = prevScopeKeyRef.current !== scopeKey
    prevScopeKeyRef.current = scopeKey

    const scopedBootstrap = getPortalCacheBootstrap<PortalDashboardPortfolioPayload>(portfolioCacheKey)

    if (scopeChanged) {
      setPortfolio(scopedBootstrap.data)
      setPortfolioLoading(!scopedBootstrap.hasInitialData)
      const currency = resolvePortfolioCurrencyFromCore(coreRef.current)
      void loadPortfolio(currency || undefined, !scopedBootstrap.hasInitialData)
      return
    }

    const coreBootstrap = getPortalCacheBootstrap<PortalDashboardCorePayload>(DASHBOARD_CORE_CACHE_KEY)
    let cancelled = false

    const runCore = () => {
      if (cancelled) return
      void loadCore(false)
    }
    const runPortfolio = () => {
      if (cancelled) return
      const currency = resolvePortfolioCurrencyFromCore(coreRef.current)
      void loadPortfolio(currency || undefined, false)
    }

    if (coreBootstrap.isFresh && coreBootstrap.data) {
      scheduleIdleRevalidate(runCore)
    } else {
      runCore()
    }

    if (scopedBootstrap.isFresh && scopedBootstrap.data) {
      scheduleIdleRevalidate(runPortfolio)
    } else {
      runPortfolio()
    }

    return () => {
      cancelled = true
    }
  }, [loadCore, loadPortfolio, portfolioCacheKey, scopeRevision, scopeSuffix])

  const data = useMemo(
    () => mergePortalDashboardPayload(core, portfolio),
    [core, portfolio],
  )

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      const nextCore = await loadCore(true)
      await loadPortfolio(resolvePortfolioCurrencyFromCore(nextCore), true)
    } finally {
      setRefreshing(false)
    }
  }, [loadCore, loadPortfolio])

  return { data, loading, portfolioLoading, refreshing, error, refresh }
}
