import { PORTAL_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import { readPortalCache } from '@/lib/portal/portalClientCache'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'

export type ResolveInvestHubBundlesInput = {
  marketsData: PortalMarketsPayload | null
  readMarketsCache?: () => PortalMarketsPayload | null
}

export type ResolveInvestHubBundlesResult = {
  effectiveMarketsData: PortalMarketsPayload | null
  bundles: PortalMarketsPayload['bundles']
  usedMarketsFallback: boolean
}

/** Résout les paniers Invest : hook invest-markets d’abord, puis cache Markets (G4-B2). */
export function resolveInvestHubBundles(
  input: ResolveInvestHubBundlesInput,
): ResolveInvestHubBundlesResult {
  const readMarketsCache = input.readMarketsCache ?? (() => readPortalCache<PortalMarketsPayload>(PORTAL_CACHE_KEYS.markets))

  if (input.marketsData) {
    return {
      effectiveMarketsData: input.marketsData,
      bundles: input.marketsData.bundles ?? [],
      usedMarketsFallback: false,
    }
  }

  const fallback = readMarketsCache()
  if (fallback) {
    return {
      effectiveMarketsData: fallback,
      bundles: fallback.bundles ?? [],
      usedMarketsFallback: true,
    }
  }

  return {
    effectiveMarketsData: null,
    bundles: [],
    usedMarketsFallback: false,
  }
}

/** Skeleton plein écran Invest uniquement tant que les offres ne sont pas disponibles. */
export function shouldShowInvestFullSkeleton(investLoading: boolean, investData: unknown): boolean {
  return investLoading && investData == null
}

export type InvestHubMarketsSectionLoadingInput = {
  marketsLoading: boolean
  bundleCount: number
}

/** Paniers / coffres bundle : skeleton section si marchés en vol et aucun bundle (y compris fallback). */
export function shouldShowInvestMarketsBundlesSectionLoading(
  input: InvestHubMarketsSectionLoadingInput,
): boolean {
  return input.marketsLoading && input.bundleCount === 0
}

export type InvestHubDefiVaultsSectionLoadingInput = {
  showDeFiVaults: boolean
  defiVaultsLoading: boolean
  defiVaultCount: number
}

/** Morpho / Ledgity : skeleton section DeFi tant que vaults non résolus. */
export function shouldShowInvestDefiVaultsSectionLoading(
  input: InvestHubDefiVaultsSectionLoadingInput,
): boolean {
  return input.showDeFiVaults && input.defiVaultsLoading && input.defiVaultCount === 0
}
