'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
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
 */
export function usePortalCachedScreen<T>(options: {
  cacheKey: string
  url: string
  ttlMs: number
  errorMessage: string
}): UsePortalCachedScreenResult<T> {
  const { cacheKey, url, ttlMs, errorMessage } = options
  const router = useRouter()
  const bootstrapRef = useRef(getPortalCacheBootstrap<T>(cacheKey))

  const [data, setData] = useState<T | null>(() => bootstrapRef.current.data)
  const [loading, setLoading] = useState(() => !bootstrapRef.current.hasInitialData)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const dataRef = useRef(data)
  dataRef.current = data

  const revalidate = useCallback(
    async (isManualRefresh: boolean) => {
      const hasDisplayedData = dataRef.current !== null

      if (isManualRefresh) {
        setRefreshing(true)
      } else if (!hasDisplayedData) {
        setLoading(true)
      }

      setError('')
      try {
        const json = await revalidatePortalCache<T>(cacheKey, url, ttlMs)
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
    [cacheKey, url, ttlMs, errorMessage, router],
  )

  useEffect(() => {
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
  }, [revalidate])

  const refresh = useCallback(async () => {
    await revalidate(true)
  }, [revalidate])

  return { data, setData, loading, refreshing, error, refresh }
}
