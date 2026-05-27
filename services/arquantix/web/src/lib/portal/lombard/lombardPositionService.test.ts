import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  buildLombardActivePositionRow,
  buildLombardPositionsPayload,
  isLombardOnchainPositionActive,
} from '@/lib/portal/lombard/lombardPositionService'
import type { LombardMorphoMarketRow } from '@/lib/portal/lombard/lombardGraphql'

const cbBtcMarket = VANCELIAN_LOMBARD_V1.markets[0]

const gqlFixture: LombardMorphoMarketRow = {
  marketId: cbBtcMarket.marketId,
  loanAsset: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', symbol: 'USDC', decimals: 6 },
  collateralAsset: {
    address: '0xcbB7c0000aB88B473b1f5aFd9ef808440eed33Bf',
    symbol: 'cbBTC',
    decimals: 8,
  },
  lltv: '860000000000000000',
  oracle: { address: '0x663BECd10daE6C4A3Dcd89F1d76c1174199639B9' },
  irmAddress: '0x46415998764C29aB2a25CbeA6254146D50D22687',
  state: { borrowApy: 0.048, borrowAssets: '1000', liquidityAssets: '5000' },
}

describe('lombardPositionService', () => {
  it('isLombardOnchainPositionActive', () => {
    assert.equal(
      isLombardOnchainPositionActive({ collateralRaw: BigInt(0), borrowRaw: BigInt(0) }),
      false,
    )
    assert.equal(
      isLombardOnchainPositionActive({ collateralRaw: BigInt(1), borrowRaw: BigInt(0) }),
      true,
    )
  })

  it('buildLombardActivePositionRow maps health and amounts', () => {
    const row = buildLombardActivePositionRow({
      marketConfig: cbBtcMarket,
      gql: gqlFixture,
      collateralAmountRaw: BigInt('25000000'),
      borrowAmountRaw: BigInt('15000000000'),
      currentLtvWad: BigInt('480000000000000000'),
      liquidationPriceRaw: null,
    })

    assert.ok(row)
    assert.equal(row?.collateralSymbol, 'cbBTC')
    assert.equal(row?.borrowAmount, '15000')
    assert.equal(row?.healthStatus, 'comfortable')
    assert.equal(row?.healthLabel, 'Comfortable')
    assert.equal(row?.currentLtvPercent, 48)
    assert.equal(row?.morphoLltvPercent, 86)
  })

  it('buildLombardPositionsPayload flags active loan', () => {
    const row = buildLombardActivePositionRow({
      marketConfig: cbBtcMarket,
      gql: gqlFixture,
      collateralAmountRaw: BigInt('25000000'),
      borrowAmountRaw: BigInt('15000000000'),
      currentLtvWad: BigInt('650000000000000000'),
      liquidationPriceRaw: null,
    })
    assert.ok(row)
    const payload = buildLombardPositionsPayload({
      enabled: true,
      walletAddress: '0x0000000000000000000000000000000000000001',
      positions: row ? [row] : [],
    })
    assert.equal(payload.hasActiveLoan, true)
    assert.equal(payload.positions.length, 1)
  })
})
