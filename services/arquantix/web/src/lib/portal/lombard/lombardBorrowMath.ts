import type { AccrualPosition, Market } from '@morpho-org/blue-sdk'

/** Aligné sur le +1 share/assets du SDK Morpho (`validatePositionHealth`). */
export const LOMBARD_BORROW_ASSETS_ROUNDING_BUFFER = BigInt(1)

export type LombardPositionBorrowSnapshot = {
  collateralRaw: bigint
  borrowAssetsRaw: bigint
}

export function readLombardPositionBorrowSnapshot(position: AccrualPosition): LombardPositionBorrowSnapshot {
  return {
    collateralRaw: position.collateral,
    borrowAssetsRaw: position.borrowAssets,
  }
}

export function emptyLombardPositionBorrowSnapshot(): LombardPositionBorrowSnapshot {
  return { collateralRaw: BigInt(0), borrowAssetsRaw: BigInt(0) }
}

export function computeMaxTotalBorrowRaw(args: {
  marketData: Market
  totalCollateralRaw: bigint
  maxLtvWad: bigint
}): bigint | null {
  const maxBorrow = args.marketData.getMaxBorrowAssets(args.totalCollateralRaw, { maxLtv: args.maxLtvWad })
  return maxBorrow ?? null
}

export function computeMaxIncrementalBorrowRaw(args: {
  marketData: Market
  position: LombardPositionBorrowSnapshot
  walletCollateralRaw: bigint
  maxLtvWad: bigint
}): bigint | null {
  const maxTotalBorrow = computeMaxTotalBorrowRaw({
    marketData: args.marketData,
    totalCollateralRaw: args.position.collateralRaw + args.walletCollateralRaw,
    maxLtvWad: args.maxLtvWad,
  })
  if (maxTotalBorrow == null) return null

  const incremental = maxTotalBorrow - args.position.borrowAssetsRaw
  return incremental > BigInt(0) ? incremental : BigInt(0)
}

export function findMinimumIncrementalCollateralForBorrow(args: {
  marketData: Market
  position: LombardPositionBorrowSnapshot
  borrowAmountRaw: bigint
  maxLtvWad: bigint
  walletCollateralRaw: bigint
}): bigint | null {
  if (args.borrowAmountRaw <= BigInt(0) || args.walletCollateralRaw <= BigInt(0)) {
    return null
  }

  const targetTotalBorrow =
    args.position.borrowAssetsRaw + args.borrowAmountRaw + LOMBARD_BORROW_ASSETS_ROUNDING_BUFFER

  let low = BigInt(1)
  let high = args.walletCollateralRaw
  let best: bigint | null = null

  for (let i = 0; i < 96; i += 1) {
    const mid = (low + high) / BigInt(2)
    const totalCollateral = args.position.collateralRaw + mid
    const maxBorrow = args.marketData.getMaxBorrowAssets(totalCollateral, { maxLtv: args.maxLtvWad })
    if (maxBorrow != null && maxBorrow >= targetTotalBorrow) {
      best = mid
      high = mid - BigInt(1)
    } else {
      low = mid + BigInt(1)
    }
    if (low > high) break
  }

  return best
}

export function computeProjectedPositionLtvRatio(args: {
  marketData: Market
  position: LombardPositionBorrowSnapshot
  additionalCollateralRaw: bigint
  additionalBorrowRaw: bigint
}): number | null {
  const totalCollateral = args.position.collateralRaw + args.additionalCollateralRaw
  const collateralValue = args.marketData.getCollateralValue(totalCollateral)
  if (collateralValue == null || collateralValue <= BigInt(0)) return null

  const totalBorrow = args.position.borrowAssetsRaw + args.additionalBorrowRaw
  return Number(totalBorrow) / Number(collateralValue)
}
