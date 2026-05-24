import type { MorphoReconciliationStatus } from '@prisma/client'

import { compareMorphoReconciliationAssets } from '@/lib/portal/morphoVaultMonitoring'

/** Utilitaire test — délègue à compareMorphoReconciliationAssets. */
export function compareAssetsForTest(args: {
  ledgerAssetsRaw: string | null
  onchainAssetsRaw: string | null
  toleranceRaw?: bigint
}): MorphoReconciliationStatus {
  return compareMorphoReconciliationAssets(args)
}
