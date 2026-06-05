'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  appendPortalScopeQuery,
  buildPortalScopeCacheSuffix,
} from '@/lib/portal/portalScopeQuery'
import { usePortalScopeRevision } from '@/lib/portal/portalScopeReload'
import {
  getPortalCacheBootstrap,
  PortalFetchError,
  revalidatePortalCache,
} from '@/lib/portal/portalClientCache'

export type UsePortalCachedScreenResult<T> = {
  data: T | null
  setData: React.Dispatch<React.SetStateAction<T | null>>
  loading: boolean
  refreshing: boolean
  error: string
  refresh: () => Promise<void>
}

/**
 * Charge un écran portail avec :
 * - init synchrone depuis le cache mémoire (pas de flash skeleton)
 * - revalidation réseau en arrière-plan au montage (stale-while-revalidate)
 * - `scopeAware` : cache + URL scoping par réseau / wallet navbar, reload au changement
 */
export function usePortalCachedScreen<T>(options: {
  cacheKey: string
  url: string
  ttlMs: number
  errorMessage: string
  scopeAware?: boolean
}): UsePortalCachedScreenResult<T> {
  const { cacheKey, url, ttlMs, errorMessage, scopeAware = false } = options
  const router = useRouter()
  const { chain } = usePortalChainContext()
  const { walletScope, walletScopeId } = usePortalWalletScopeContext()
  const scopeRevision = usePortalScopeRevision()

  const scopeSuffix = scopeAware
    ? buildPortalScopeCacheSuffix(chain, walletScopeId)
    : null
  const resolvedCacheKey = scopeSuffix ? `${cacheKey}:${scopeSuffix}` : cacheKey
  const resolvedUrl = scopeAware ? appendPortalScopeQuery(url, chain, walletScope) : url

  const bootstrapRef = useRef(getPortalCacheBootstrap<T>(resolvedCacheKey))
  const prevScopeKeyRef = useRef(`${scopeSuffix ?? ''}:${scopeRevision}`)

  const [data, setData] = useState<T | null>(() => bootstrapRef.current.data)
  const [loading, setLoading] = useState(() => !bootstrapRef.current.hasInitialData)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const dataRef = useRef(data)
  dataRef.current = data

  const revalidate = useCallback(
    async (isManualRefresh: boolean) => {
      const hasDisplayedData = dataRef.current !== null
      const bootstrap = getPortalCacheBootstrap<T>(resolvedCacheKey)
      const staleWhileDisplayed = hasDisplayedData && !bootstrap.isFresh

      if (isManualRefresh) {
        setRefreshing(true)
      } else if (!hasDisplayedData) {
        setLoading(true)
      } else if (staleWhileDisplayed) {
        setRefreshing(true)
      }

      setError('')
      try {
        const json = await revalidatePortalCache<T>(resolvedCacheKey, resolvedUrl, ttlMs)
        setData(json)
      } catch (err) {
        if (err instanceof PortalFetchError && err.status === 401) {
          router.replace(PORTAL_ROUTES.login)
          return
        }
        if (!hasDisplayedData) {
          setError(errorMessage)
        }
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [errorMessage, resolvedCacheKey, resolvedUrl, router, ttlMs],
  )

  useEffect(() => {
    bootstrapRef.current = getPortalCacheBootstrap<T>(resolvedCacheKey)
    const scopeKey = `${scopeSuffix ?? ''}:${scopeRevision}`
    const scopeChanged = prevScopeKeyRef.current !== scopeKey
    prevScopeKeyRef.current = scopeKey

    if (scopeChanged && scopeAware) {
      setData(bootstrapRef.current.data)
      setLoading(!bootstrapRef.current.hasInitialData)
      void revalidate(true)
      return
    }

    const bootstrap = bootstrapRef.current
    if (bootstrap.isFresh) {
      const schedule =
        typeof requestIdleCallback !== 'undefined'
          ? (cb: () => void) => requestIdleCallback(cb, { timeout: 2500 })
          : (cb: () => void) => window.setTimeout(cb, 120)
      schedule(() => void revalidate(false))
      return
    }
    void revalidate(false)
  }, [revalidate, resolvedCacheKey, scopeAware, scopeRevision, scopeSuffix])

  const refresh = useCallback(async () => {
    await revalidate(true)
  }, [revalidate])

  return { data, setData, loading, refreshing, error, refresh }
}
