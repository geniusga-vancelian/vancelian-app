import {
  buildPortalInvestOffers,
  buildPortalInvestVaults,
} from '@/lib/portal/investFormat'
import type {
  PortalInvestOffersPayload,
  PortalInvestVaultsPayload,
} from '@/lib/portal/investTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'

/** Catalogue produit pouvait timeouter à 20s ; on garde 20s, fail-soft par section. */
export const PORTAL_INVEST_FETCH_TIMEOUT_MS = 20_000

async function fetchCatalogProducts(
  origin: string,
  type: 'exclusive_offer' | 'vault_simple',
  locale: string,
): Promise<{ ok: boolean; products: unknown[] }> {
  const catalogBase = `${origin}/api/mobile/flutter/catalog/products`
  const qs = `type=${type}&locale=${encodeURIComponent(locale)}&include_engine_data=true&limit=50`
  try {
    const res = await fetch(`${catalogBase}?${qs}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(PORTAL_INVEST_FETCH_TIMEOUT_MS),
    })
    const json = await res.json().catch(() => null)
    const products = (json as { products?: unknown[] })?.products ?? []
    return { ok: res.ok, products: Array.isArray(products) ? products : [] }
  } catch {
    return { ok: false, products: [] }
  }
}

/** Offres exclusives (catalog `exclusive_offer`). Section progressive, fail-soft. */
export async function loadPortalInvestOffers(
  origin: string,
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalInvestOffersPayload> {
  const res = await fetchCatalogProducts(origin, 'exclusive_offer', locale)
  return {
    offers: buildPortalInvestOffers(res.products as never[]),
    partial: !res.ok,
  }
}

/** Coffres catalogue (catalog `vault_simple`). Section progressive, fail-soft. */
export async function loadPortalInvestVaults(
  origin: string,
  locale: string = PORTAL_CONTENT_LOCALE,
): Promise<PortalInvestVaultsPayload> {
  const res = await fetchCatalogProducts(origin, 'vault_simple', locale)
  return {
    vaults: buildPortalInvestVaults(res.products as never[]),
    partial: !res.ok,
  }
}
