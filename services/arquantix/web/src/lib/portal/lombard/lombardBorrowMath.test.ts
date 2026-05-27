import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { Market } from '@morpho-org/blue-sdk'

import {
  computeMaxIncrementalBorrowRaw,
  computeProjectedPositionLtvRatio,
  emptyLombardPositionBorrowSnapshot,
  findMinimumIncrementalCollateralForBorrow,
} from '@/lib/portal/lombard/lombardBorrowMath'

const MAX_LTV_WAD = BigInt(550_000_000_000_000_000) // 55%

function mockMarket(args: { collateralUsdPerUnit?: bigint; ltvWad?: bigint } = {}): Market {
  const collateralUsdPerUnit = args.collateralUsdPerUnit ?? BigInt(400_000) // 0.4 USDC per 1 raw cbBTC unit (illustrative)
  const ltvWad = args.ltvWad ?? MAX_LTV_WAD

  return {
    getCollateralValue(collateral: bigint) {
      return collateral * collateralUsdPerUnit
    },
    getMaxBorrowAssets(collateral: bigint, options?: { maxLtv?: bigint }) {
      const value = collateral * collateralUsdPerUnit
      const ltv = options?.maxLtv ?? ltvWad
      return (value * ltv) / BigInt(10) ** BigInt(18)
    },
  } as unknown as Market
}

describe('lombardBorrowMath', () => {
  it('treats an empty position like a first borrow', () => {
    const marketData = mockMarket()
    const position = emptyLombardPositionBorrowSnapshot()
    const walletCollateralRaw = BigInt(100_000)

    const maxBorrow = computeMaxIncrementalBorrowRaw({
      marketData,
      position,
      walletCollateralRaw,
      maxLtvWad: MAX_LTV_WAD,
    })
    assert.ok(maxBorrow != null && maxBorrow > BigInt(0))

    const guarantee = findMinimumIncrementalCollateralForBorrow({
      marketData,
      position,
      borrowAmountRaw: BigInt(8_000_000),
      maxLtvWad: MAX_LTV_WAD,
      walletCollateralRaw,
    })
    assert.ok(guarantee != null && guarantee > BigInt(0))

    const projected = computeProjectedPositionLtvRatio({
      marketData,
      position,
      additionalCollateralRaw: guarantee,
      additionalBorrowRaw: BigInt(8_000_000),
    })
    assert.ok(projected != null && projected <= 0.55 + 1e-6)
  })

  it('accounts for existing collateral and debt on incremental borrows', () => {
    const marketData = mockMarket()
    const position = {
      collateralRaw: BigInt(23_790),
      borrowAssetsRaw: BigInt(10_000_000),
    }
    const walletCollateralRaw = BigInt(42_560)

    const maxBorrow = computeMaxIncrementalBorrowRaw({
      marketData,
      position,
      walletCollateralRaw,
      maxLtvWad: MAX_LTV_WAD,
    })
    assert.ok(maxBorrow != null)

    const guarantee = findMinimumIncrementalCollateralForBorrow({
      marketData,
      position,
      borrowAmountRaw: BigInt(8_000_000),
      maxLtvWad: MAX_LTV_WAD,
      walletCollateralRaw,
    })
    assert.ok(guarantee != null && guarantee > BigInt(0))

    const projected = computeProjectedPositionLtvRatio({
      marketData,
      position,
      additionalCollateralRaw: guarantee,
      additionalBorrowRaw: BigInt(8_000_000),
    })
    assert.ok(projected != null && projected <= 0.55 + 1e-6)
  })
})
