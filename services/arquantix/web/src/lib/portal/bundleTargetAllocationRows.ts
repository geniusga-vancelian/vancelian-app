import type { PortalBundleAllocationRow } from '@/components/portal/bundles/PortalBundleTargetAllocation'
import { displayBundleAssetSymbol } from '@/lib/portal/bundleFormat'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'

/** Lignes donut — allocation cible théorique du panier (pourcentages uniquement). */
export function buildBundleTargetAllocationRows(
  bundle: Pick<PortalCryptoBundle, 'targetAllocations' | 'allocationTickers'>,
): PortalBundleAllocationRow[] {
  const source =
    bundle.targetAllocations?.length > 0
      ? bundle.targetAllocations
      : (bundle.allocationTickers ?? []).map((assetSymbol) => ({
          assetSymbol,
          targetWeight: 0,
        }))

  if (source.length === 0) return []

  const needsEqualSplit = source.every((row) => !row.targetWeight || row.targetWeight <= 0)
  const equalWeight = needsEqualSplit && source.length > 0 ? 1 / source.length : 0

  return source.map((row) => ({
    asset: row.assetSymbol,
    assetDisplay: displayBundleAssetSymbol(row.assetSymbol),
    targetWeight: row.targetWeight > 0 ? row.targetWeight : equalWeight,
  }))
}
