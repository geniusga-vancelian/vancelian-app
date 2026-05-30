import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatCreditLineBalanceLabel,
  resolveCreditLineFromPositions,
  resolveCreditLineSubtitle,
} from '@/lib/portal/lombard/lombardCreditLineFormat'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'

const samplePosition = (borrowAmount: string): LombardActivePosition => ({
  marketId: 'm1',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.001',
  collateralAmountRaw: '100000',
  collateralUsdValue: '90',
  borrowSymbol: 'USDC',
  borrowAmount,
  borrowAmountRaw: '25000000',
  currentLtvPercent: 55,
  maxUserLtvPercent: 70,
  morphoLltvPercent: 86,
  healthStatus: 'safe',
  healthLabel: 'Sain',
  healthMessage: 'OK',
  borrowApyPercent: 5.2,
  borrowApyLabel: '5.2% variable',
  liquidationPrice: null,
  protocolLabel: 'Powered by Morpho',
  chainId: 8453,
})

describe('lombardCreditLineFormat', () => {
  it('formats small USDC debt with extra precision', () => {
    assert.match(formatCreditLineBalanceLabel(40.002631), /40,002631/)
    assert.match(formatCreditLineBalanceLabel(40.002631), /USDC/)
  })

  it('sums outstanding Morpho borrow positions', () => {
    const summary = resolveCreditLineFromPositions([
      samplePosition('25.002204'),
      samplePosition('15.000427'),
    ])
    assert.equal(summary.totalBorrowedUsdc, 40.002631)
    assert.equal(summary.loanCount, 2)
    assert.equal(summary.visible, true)
    assert.match(summary.subtitle, /2 loans/)
  })

  it('hides credit line when no outstanding debt', () => {
    const summary = resolveCreditLineFromPositions([])
    assert.equal(summary.visible, false)
    assert.equal(resolveCreditLineSubtitle(0), 'Liquidity advances · Morpho')
  })
})
