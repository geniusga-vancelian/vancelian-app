'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'

import { PortalDashboardLayout } from '@/components/portal/dashboard/PortalDashboardLayout'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalMarketsSkeleton } from '@/components/portal/PortalRouteSkeleton'
import { PortalPageIntro } from '@/components/portal/PortalPageIntro'
import { PortalTopCryptoSection } from '@/components/portal/markets/PortalTopCryptoSection'
import { applyQuoteUpdates } from '@/lib/portal/marketsFormat'
import { Container } from '@/components/ui/Container'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import type { PortalCryptoAsset } from '@/lib/portal/marketsTypes'
import {
  getPortalCacheBootstrap,
  writePortalCache,
} from '@/lib/portal/portalClientCache'
import { useMarketDataQuotesWs } from '@/lib/portal/useMarketDataQuotesWs'
import { cn } from '@/lib/utils'

const ALL_CRYPTO_CACHE_KEY = 'portal:all-crypto:v2'

export function PortalAllCryptoScreen() {
  const router = useRouter()
  const bootstrap = getPortalCacheBootstrap<PortalCryptoAsset[]>(ALL_CRYPTO_CACHE_KEY)
  const [assets, setAssets] = useState<PortalCryptoAsset[]>(bootstrap.data ?? [])
  const [loading, setLoading] = useState(!bootstrap.hasInitialData)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [marketDataBaseUrl, setMarketDataBaseUrl] = useState<string | undefined>()

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else if (!bootstrap.hasInitialData) setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/portal/markets/all-crypto', { credentials: 'include' })
      if (res.status === 401) {
        router.replace(PORTAL_ROUTES.login)
        return
      }
      if (!res.ok) {
        setError('Unable to load crypto instruments.')
        return
      }
      const json = (await res.json()) as {
        items?: PortalCryptoAsset[]
        marketDataPublicBaseUrl?: string
      }
      const items = json.items ?? []
      writePortalCache(ALL_CRYPTO_CACHE_KEY, items, 120_000)
      setAssets(items)
      if (json.marketDataPublicBaseUrl) {
        setMarketDataBaseUrl(json.marketDataPublicBaseUrl)
      }
    } catch {
      setError('Unable to load crypto instruments.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [bootstrap.hasInitialData, router])

  useEffect(() => {
    void load()
  }, [load])

  const wsSymbols = useMemo(
    () => assets.map((asset) => asset.symbol).filter(Boolean),
    [assets],
  )

  const handleWsQuotes = useCallback(
    (updates: Parameters<typeof applyQuoteUpdates>[1]) => {
      setAssets((prev) => applyQuoteUpdates(prev, updates, 'USD'))
    },
    [],
  )

  useMarketDataQuotesWs(
    wsSymbols,
    handleWsQuotes,
    assets.length > 0,
    marketDataBaseUrl,
  )

  if (loading && assets.length === 0) return <PortalMarketsSkeleton />

  if (error && assets.length === 0) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
        <button
          type="button"
          onClick={() => void load(true)}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Retry
        </button>
      </Container>
    )
  }

  return (
    <PortalPageContainer>
      <PortalDashboardLayout>
        <PortalReveal index={0}>
          <PortalPageIntro
            eyebrow="Markets"
            title="All crypto"
            description="Full list of crypto instruments available on Vancelian."
          />
        </PortalReveal>

        <PortalReveal index={1}>
          <PortalTopCryptoSection
            popular={[]}
            topGainers={[]}
            topLosers={[]}
            favorites={[]}
            assets={assets}
            showTabs={false}
            showBrowseLink={false}
            title="All crypto"
            loading={loading}
            error={error ?? undefined}
            onRetry={() => void load(true)}
            emptyMessage="No crypto instruments are available."
          />
        </PortalReveal>

        <button
          type="button"
          disabled={refreshing}
          onClick={() => void load(true)}
          className={cn(
            'v-text-link w-fit border-0 bg-transparent p-0 font-ui text-[13px]',
            refreshing && 'opacity-50',
          )}
        >
          {refreshing ? 'Refreshing…' : 'Refresh list'}
        </button>
      </PortalDashboardLayout>
    </PortalPageContainer>
  )
}
