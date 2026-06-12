import { readPortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_SECTION_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import type {
  PortalInvestOffersPayload,
  PortalInvestPayload,
  PortalInvestVaultsPayload,
} from '@/lib/portal/investTypes'

/**
 * Reconstruit un payload invest composite depuis les caches de section
 * (offers + vaults) pour la preview de navigation stale-while-navigate.
 * Retourne null tant qu'aucune section n'est en cache.
 */
export function readPortalInvestPayloadFromCache(): PortalInvestPayload | null {
  const offers = readPortalCache<PortalInvestOffersPayload>(PORTAL_SECTION_CACHE_KEYS.investOffers)
  const vaults = readPortalCache<PortalInvestVaultsPayload>(PORTAL_SECTION_CACHE_KEYS.investVaults)

  if (!offers && !vaults) return null

  return {
    offers: offers?.offers ?? [],
    vaults: vaults?.vaults ?? [],
    partial: Boolean(offers?.partial || vaults?.partial),
  }
}
