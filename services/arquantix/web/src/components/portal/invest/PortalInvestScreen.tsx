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
import type {
  PortalInvestOffersPayload,
  PortalInvestVaultsPayload,
} from '@/lib/portal/investTypes'
import { fetchPortalMorphoVaults } from '@/lib/portal/morphoVaultClient'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { usePortalChainContext } from '@/lib/portal/portalChainContext'
import { isPortalChainDeFiEnabled } from '@/lib/portal/portalChainFilter'
import {
  PORTAL_CACHE_KEYS,
  PORTAL_SECTION_CACHE_KEYS,
} from '@/lib/portal/portalCacheKeys'
import {
  resolveInvestHubBundles,
  shouldShowInvestDefiVaultsSectionLoading,
  shouldShowInvestMarketsBundlesSectionLoading,
} from '@/lib/portal/portalInvestProgressiveData'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { usePortalProgressiveSections } from '@/lib/portal/usePortalProgressiveSections'
import { fetchPortalLedgityVaults } from '@/lib/portal/ledgity/ledgityVaultClient'
import { cn } from '@/lib/utils'

const MARKETS_CACHE_KEY = PORTAL_CACHE_KEYS.investMarkets

type InvestSections = {
  offers: PortalInvestOffersPayload
  vaults: PortalInvestVaultsPayload
}

export function PortalInvestScreen() {
  const { chain } = usePortalChainContext()
  const showDeFiVaults = isPortalChainDeFiEnabled(chain)

  // Offres et coffres catalogue chargés indépendamment : chacun arrive avec son
  // propre shimmer, et l'échec d'une section n'impacte pas l'autre ni la page.
  const {
    sections,
    refreshing: investRefreshing,
    refresh: refreshInvest,
  } = usePortalProgressiveSections<InvestSections>({
    offers: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.investOffers,
      url: `/api/portal/invest/offers?locale=${PORTAL_CONTENT_LOCALE}`,
      ttlMs: 120_000,
      errorMessage: 'Unable to load investment offers.',
    },
    vaults: {
      cacheKey: PORTAL_SECTION_CACHE_KEYS.investVaults,
      url: `/api/portal/invest/vaults?locale=${PORTAL_CONTENT_LOCALE}`,
      ttlMs: 120_000,
      errorMessage: 'Unable to load vaults.',
    },
  })

  const offersSection = sections.offers
  const vaultsSection = sections.vaults
  const offers = useMemo(() => offersSection.data?.offers ?? [], [offersSection.data])
  const vaultProducts = useMemo(() => vaultsSection.data?.vaults ?? [], [vaultsSection.data])

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

  const hasAnyInvestData = offersSection.data != null || vaultsSection.data != null
  const offersLoading = offersSection.loading && offers.length === 0
  const vaultsLoading = vaultsSection.loading && vaultProducts.length === 0

  // Skeleton plein écran uniquement au tout premier rendu (aucune section résolue).
  if (!hasAnyInvestData && (offersSection.loading || vaultsSection.loading)) {
    return <PortalInvestSkeleton />
  }

  // Échec total : les deux sections en erreur sans aucune donnée (cas rare réseau).
  if (!hasAnyInvestData && offersSection.error && vaultsSection.error) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{offersSection.error}</p>
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

  return (
    <PortalPageContainer>
      <PortalReveal index={0}>
        <PortalPlacerView
          offers={offers}
          vaultProducts={vaultProducts}
          coffreBundles={coffreBundles}
          panierBundles={panierBundles}
          defiVaults={defiVaults}
          showDeFiVaults={false}
          offersLoading={offersLoading}
          vaultsLoading={vaultsLoading}
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
