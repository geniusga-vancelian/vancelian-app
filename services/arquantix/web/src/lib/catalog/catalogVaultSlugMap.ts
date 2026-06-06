import {
  VANCELIAN_AXBALI_VAULT,
  VANCELIAN_AXDUBAI_VAULT,
  VANCELIAN_AXUSD_VAULT,
  VANCELIAN_VFEUR_VAULT,
  normalizeVaultAddress,
} from '@/lib/portal/ledgity/ledgityConstants'

/** Slugs catalogue `vault_simple` / offres → adresse on-chain connue (fallback snapshot). */
const CATALOG_SLUG_VAULT_ADDRESS: Record<string, string> = {
  vancelianflexvault: VANCELIAN_VFEUR_VAULT,
  'vancelian-flex-vault': VANCELIAN_VFEUR_VAULT,
  vancelianflexiblevault: VANCELIAN_VFEUR_VAULT,
  vancelianflexiblevaulteurc: VANCELIAN_VFEUR_VAULT,
  arquantixyieldusdc: VANCELIAN_AXUSD_VAULT,
  arquantixdubai: VANCELIAN_AXDUBAI_VAULT,
  arquantixbali: VANCELIAN_AXBALI_VAULT,
}

export function resolveCatalogSlugVaultAddress(slug: string | null | undefined): string | null {
  const key = slug?.trim().toLowerCase()
  if (!key) return null
  const address = CATALOG_SLUG_VAULT_ADDRESS[key]
  return address ? normalizeVaultAddress(address) : null
}

/** Slug catalogue depuis l’adresse on-chain (lien fiche produit position épargne). */
export function resolveCatalogVaultSlugByAddress(vaultAddress: string | null | undefined): string | null {
  const normalized = vaultAddress?.trim().toLowerCase()
  if (!normalized) return null
  for (const [slug, address] of Object.entries(CATALOG_SLUG_VAULT_ADDRESS)) {
    if (normalizeVaultAddress(address) === normalized) return slug
  }
  return null
}
