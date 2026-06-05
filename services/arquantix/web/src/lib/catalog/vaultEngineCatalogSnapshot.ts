/**
 * Snapshot VAULT_ENGINE pour le catalogue — serveur uniquement (API routes).
 * Ne pas importer depuis des modules client (évite node:crypto via ledgity sandbox).
 */
import { fetchVaultEngineSnapshot } from '@/lib/admin/platformVaultEngine'

export async function fetchVaultEngineSnapshotForCatalog(
  portalConfigId: string,
  options?: { catalogSlug?: string | null },
): Promise<Record<string, unknown> | null> {
  const snap = await fetchVaultEngineSnapshot(portalConfigId, options)
  return snap ? (snap as unknown as Record<string, unknown>) : null
}
