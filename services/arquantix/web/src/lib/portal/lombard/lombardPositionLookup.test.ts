import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  findLombardPositionByCollateral,
  findLombardPositionByMarketId,
} from './lombardPositionLookup'
import type { LombardActivePosition } from './lombardPositionTypes'

const samplePosition: LombardActivePosition = {
  marketId: '0xabc',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.1',
  collateralAmountRaw: '10000000',
  collateralUsdValue: '9000',
  borrowSymbol: 'USDC',
  borrowAmount: '100',
  borrowAmountRaw: '100000000',
  currentLtvPercent: 40,
  maxUserLtvPercent: 70,
  morphoLltvPercent: 86,
  healthStatus: 'healthy',
  healthLabel: 'Healthy',
  healthMessage: 'OK',
  borrowApyPercent: 5,
  borrowApyLabel: '5%',
  liquidationPrice: '$50,000',
  protocolLabel: 'Powered by Morpho',
  chainId: 8453,
}

describe('lombardPositionLookup', () => {
  it('finds position by market id', () => {
    assert.equal(findLombardPositionByMarketId([samplePosition], '0xAbC')?.marketId, '0xabc')
  })

  it('finds position by collateral', () => {
    assert.equal(findLombardPositionByCollateral([samplePosition], 'cbbtc')?.collateralSymbol, 'cbBTC')
  })
})
