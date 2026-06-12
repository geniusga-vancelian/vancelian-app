'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { usePortalWalletScopeContext } from '@/lib/portal/portalWalletScopeContext'
import { usePortalScopeRevision } from '@/lib/portal/portalScopeReload'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import {
  appendPortalScopeQuery,
  buildPortalScopeCacheSuffix,
} from '@/lib/portal/portalScopeQuery'
import {
  getPortalCacheBootstrap,
  PortalFetchError,
  revalidatePortalCache,
} from '@/lib/portal/portalClientCache'
import {
  failSectionState,
  initSectionState,
  resetSectionState,
  startSectionState,
  succeedSectionState,
  type PortalSectionState,
} from '@/lib/portal/progressiveSectionState'

export type PortalProgressiveSectionConfig = {
  /** Clé cache mémoire (suffixée par scope si `scopeAware`). */
  cacheKey: string
  /** URL endpoint section (scope ajouté en query si `scopeAware`). */
  url: string
  ttlMs: number
  /** Recharge au changement de réseau / wallet navbar et scope cache + URL. */
  scopeAware?: boolean
  errorMessage?: string
}

export type PortalProgressiveSectionsResult<S extends Record<string, unknown>> = {
  sections: { [K in keyof S]: PortalSectionState<S[K]> }
  /** Vrai pendant un refresh manuel global. */
  refreshing: boolean
  refresh: () => Promise<void>
}

const DEFAULT_SECTION_ERROR = 'Unable to load this section.'

function scheduleIdleRevalidate(run: () => void): void {
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(run, { timeout: 2500 })
  } else if (typeof window !== 'undefined') {
    window.setTimeout(run, 120)
  } else {
    run()
  }
}

/**
 * Charge plusieurs sections d'une page en parallèle, chacune indépendante :
 * - état `loading` (shimmer) propre par section
 * - stale-while-revalidate (init synchrone depuis le cache, pas de flash)
 * - isolation des erreurs (une section qui échoue n'impacte pas les autres)
 * - scope-aware optionnel (réseau / wallet navbar) par section
 *
 * Réplique généralisé du pattern dashboard core/portfolio.
 */
export function usePortalProgressiveSections<S extends Record<string, unknown>>(
  configs: { [K in keyof S]: PortalProgressiveSectionConfig },
): PortalProgressiveSectionsResult<S> {
  const router = useRouter()
  const { chain } = usePortalChainContext()
  const { walletScope, walletScopeId } = usePortalWalletScopeContext()
  const scopeRevision = usePortalScopeRevision()

  const scopeSuffix = buildPortalScopeCacheSuffix(chain, walletScopeId)

  // Signature stable de la config : déclenche un rechargement complet si elle change.
  const signature = useMemo(() => {
    return Object.entries(configs)
      .map(
        ([key, cfg]) =>
          `${key}|${cfg.cacheKey}|${cfg.url}|${cfg.ttlMs}|${cfg.scopeAware ? 1 : 0}`,
      )
      .join('::')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(configs)])

  const configsRef = useRef(configs)
  configsRef.current = configs
  const chainRef = useRef(chain)
  chainRef.current = chain
  const walletScopeRef = useRef(walletScope)
  walletScopeRef.current = walletScope
  const scopeSuffixRef = useRef(scopeSuffix)
  scopeSuffixRef.current = scopeSuffix

  const resolveKey = useCallback((key: string): string => {
    const cfg = configsRef.current[key]
    return cfg.scopeAware ? `${cfg.cacheKey}:${scopeSuffixRef.current}` : cfg.cacheKey
  }, [])

  const resolveUrl = useCallback((key: string): string => {
    const cfg = configsRef.current[key]
    return cfg.scopeAware
      ? appendPortalScopeQuery(cfg.url, chainRef.current, walletScopeRef.current)
      : cfg.url
  }, [])

  const [states, setStates] = useState<Record<string, PortalSectionState<unknown>>>(() => {
    const initial: Record<string, PortalSectionState<unknown>> = {}
    for (const key of Object.keys(configs)) {
      const cfg = configs[key]
      const resolvedKey = cfg.scopeAware ? `${cfg.cacheKey}:${scopeSuffix}` : cfg.cacheKey
      initial[key] = initSectionState(getPortalCacheBootstrap(resolvedKey))
    }
    return initial
  })

  const statesRef = useRef(states)
  statesRef.current = states

  const [refreshing, setRefreshing] = useState(false)

  const loadSection = useCallback(
    async (key: string, isManualRefresh: boolean) => {
      const cfg = configsRef.current[key]
      if (!cfg) return
      const resolvedKey = resolveKey(key)
      const resolvedUrl = resolveUrl(key)
      const bootstrap = getPortalCacheBootstrap(resolvedKey)
      const hasDisplayed = statesRef.current[key]?.data != null

      setStates((prev) => ({
        ...prev,
        [key]: startSectionState(prev[key] ?? initSectionState(bootstrap), {
          hasDisplayed,
          isManualRefresh,
          isFresh: bootstrap.isFresh,
        }),
      }))

      try {
        const data = await revalidatePortalCache<unknown>(resolvedKey, resolvedUrl, cfg.ttlMs)
        setStates((prev) => ({ ...prev, [key]: succeedSectionState(data) }))
      } catch (err) {
        if (err instanceof PortalFetchError && err.status === 401) {
          router.replace(PORTAL_ROUTES.login)
          return
        }
        const stale = getPortalCacheBootstrap(resolvedKey)
        setStates((prev) => ({
          ...prev,
          [key]: failSectionState(prev[key] ?? initSectionState(stale), {
            staleData: stale.data,
            errorMessage: cfg.errorMessage ?? DEFAULT_SECTION_ERROR,
          }),
        }))
      }
    },
    [resolveKey, resolveUrl, router],
  )

  const prevScopeKeyRef = useRef(`${scopeSuffix}:${scopeRevision}`)
  const prevSignatureRef = useRef(signature)
  const firstRunRef = useRef(true)

  useEffect(() => {
    const scopeKey = `${scopeSuffix}:${scopeRevision}`
    const scopeChanged = prevScopeKeyRef.current !== scopeKey
    prevScopeKeyRef.current = scopeKey
    const signatureChanged = prevSignatureRef.current !== signature
    prevSignatureRef.current = signature
    const fullReload = firstRunRef.current || signatureChanged
    firstRunRef.current = false

    let cancelled = false

    for (const key of Object.keys(configsRef.current)) {
      const cfg = configsRef.current[key]
      const isScopeReload = scopeChanged && Boolean(cfg.scopeAware)
      if (!fullReload && !isScopeReload) continue

      const resolvedKey = cfg.scopeAware ? `${cfg.cacheKey}:${scopeSuffix}` : cfg.cacheKey
      const bootstrap = getPortalCacheBootstrap(resolvedKey)

      if (isScopeReload) {
        setStates((prev) => ({ ...prev, [key]: resetSectionState(bootstrap) }))
      }

      const run = () => {
        if (!cancelled) void loadSection(key, false)
      }
      if (bootstrap.isFresh && bootstrap.data) {
        scheduleIdleRevalidate(run)
      } else {
        run()
      }
    }

    return () => {
      cancelled = true
    }
  }, [loadSection, signature, scopeSuffix, scopeRevision])

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await Promise.all(
        Object.keys(configsRef.current).map((key) => loadSection(key, true)),
      )
    } finally {
      setRefreshing(false)
    }
  }, [loadSection])

  return {
    sections: states as { [K in keyof S]: PortalSectionState<S[K]> },
    refreshing,
    refresh,
  }
}
