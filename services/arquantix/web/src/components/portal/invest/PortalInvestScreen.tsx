'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalInvestSkeleton } from '@/components/portal/PortalRouteSkeleton'
import {
  isPlacerCoffreBundle,
  PortalPlacerView,
} from '@/components/portal/invest/PortalPlacerView'
import { Container } from '@/components/ui/Container'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import { fetchPortalMorphoVaults } from '@/lib/portal/morphoVaultClient'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { isPortalChainDeFiEnabled } from '@/lib/portal/portalChainFilter'
import { PORTAL_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import {
  resolveInvestHubBundles,
  shouldShowInvestDefiVaultsSectionLoading,
  shouldShowInvestFullSkeleton,
  shouldShowInvestMarketsBundlesSectionLoading,
} from '@/lib/portal/portalInvestProgressiveData'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { fetchPortalLedgityVaults } from '@/lib/portal/ledgity/ledgityVaultClient'
import { cn } from '@/lib/utils'

const INVEST_CACHE_KEY = PORTAL_CACHE_KEYS.invest
const MARKETS_CACHE_KEY = PORTAL_CACHE_KEYS.investMarkets

export function PortalInvestScreen() {
  const { chain } = usePortalChainContext()
  const showDeFiVaults = isPortalChainDeFiEnabled(chain)

  const {
    data: investData,
    loading: investLoading,
    refreshing: investRefreshing,
    error: investError,
    refresh: refreshInvest,
  } = usePortalCachedScreen<PortalInvestPayload>({
    cacheKey: INVEST_CACHE_KEY,
    url: `/api/portal/invest?locale=${PORTAL_CONTENT_LOCALE}`,
    ttlMs: 120_000,
    errorMessage: 'Unable to load investment offers.',
  })

  const { data: marketsData, loading: marketsLoading, refresh: refreshMarkets } =
    usePortalCachedScreen<PortalMarketsPayload>({
      cacheKey: MARKETS_CACHE_KEY,
      url: `/api/portal/markets?locale=${PORTAL_CONTENT_LOCALE}`,
      ttlMs: 120_000,
      errorMessage: 'Unable to load baskets.',
    })

  const [defiVaults, setDefiVaults] = useState<
    (PortalMorphoVaultDetails | PortalLedgityVaultDetails)[]
  >([])
  const [defiVaultsLoading, setDefiVaultsLoading] = useState(showDeFiVaults)

  const loadVaults = useCallback(async () => {
    if (!showDeFiVaults) {
      setDefiVaults([])
      setDefiVaultsLoading(false)
      return
    }
    setDefiVaultsLoading(true)
    try {
      const [morpho, ledgity] = await Promise.all([
        fetchPortalMorphoVaults().catch(() => ({ vaults: [] as PortalMorphoVaultDetails[] })),
        fetchPortalLedgityVaults().catch(() => ({ vaults: [] as PortalLedgityVaultDetails[] })),
      ])
      setDefiVaults([...morpho.vaults, ...ledgity.vaults])
    } catch {
      setDefiVaults([])
    } finally {
      setDefiVaultsLoading(false)
    }
  }, [showDeFiVaults])

  useEffect(() => {
    void loadVaults()
  }, [loadVaults])

  const { bundles } = useMemo(
    () => resolveInvestHubBundles({ marketsData }),
    [marketsData],
  )

  const marketsBundlesLoading = shouldShowInvestMarketsBundlesSectionLoading({
    marketsLoading,
    bundleCount: bundles.length,
  })
  const defiVaultsSectionLoading = shouldShowInvestDefiVaultsSectionLoading({
    showDeFiVaults,
    defiVaultsLoading,
    defiVaultCount: defiVaults.length,
  })

  const { coffreBundles, panierBundles } = useMemo(() => {
    const coffres = bundles.filter(isPlacerCoffreBundle)
    const paniers = bundles.filter((b) => !isPlacerCoffreBundle(b))
    return { coffreBundles: coffres, panierBundles: paniers }
  }, [bundles])

  if (shouldShowInvestFullSkeleton(investLoading, investData)) {
    return <PortalInvestSkeleton />
  }

  if (investError && !investData) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{investError}</p>
        <button
          type="button"
          onClick={() => void refreshInvest()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Try again
        </button>
      </Container>
    )
  }

  if (!investData) return null

  return (
    <PortalPageContainer>
      <PortalReveal index={0}>
        <PortalPlacerView
          offers={investData.offers}
          coffreBundles={coffreBundles}
          panierBundles={panierBundles}
          defiVaults={defiVaults}
          showDeFiVaults={showDeFiVaults}
          marketsBundlesLoading={marketsBundlesLoading}
          defiVaultsLoading={defiVaultsSectionLoading}
        />
      </PortalReveal>

      <button
        type="button"
        disabled={investRefreshing}
        onClick={() => {
          void refreshInvest()
          void refreshMarkets()
          void loadVaults()
        }}
        className={cn(
          'v-text-link mt-6 w-fit border-0 bg-transparent p-0 font-ui text-[13px]',
          investRefreshing && 'opacity-50',
        )}
      >
        {investRefreshing ? 'Refreshing…' : 'Refresh'}
      </button>
    </PortalPageContainer>
  )
}
