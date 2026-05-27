import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'

/** Helpers purs — safe côté client (pas de mock / Prisma / node:crypto). */

export function findLombardPositionByMarketId(
  positions: LombardActivePosition[],
  marketId: string,
): LombardActivePosition | null {
  const key = marketId.trim().toLowerCase()
  return positions.find((row) => row.marketId.toLowerCase() === key) ?? null
}

export function findLombardPositionByCollateral(
  positions: LombardActivePosition[],
  collateral: string,
): LombardActivePosition | null {
  const normalized = collateral.trim().toLowerCase()
  return positions.find((row) => row.collateralSymbol.toLowerCase() === normalized) ?? null
}
