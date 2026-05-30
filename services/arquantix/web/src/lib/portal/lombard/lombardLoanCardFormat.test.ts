import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  estimateLombardMonthlyInterestUsdc,
  mapLombardHealthToLoanSafety,
  resolveCreditLineSummary,
  resolveLombardHealthLabelFr,
} from '@/lib/portal/lombard/lombardLoanCardFormat'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'

const samplePosition = (overrides: Partial<LombardActivePosition> = {}): LombardActivePosition => ({
  marketId: 'm1',
  collateralSymbol: 'cbBTC',
  collateralDisplayName: 'Bitcoin',
  collateralAmount: '0.000608',
  collateralAmountRaw: '60800',
  collateralUsdValue: '50',
  borrowSymbol: 'USDC',
  borrowAmount: '25.002204',
  borrowAmountRaw: '25002204',
  currentLtvPercent: 56,
  maxUserLtvPercent: 70,
  morphoLltvPercent: 86,
  healthStatus: 'monitor',
  healthLabel: 'To monitor',
  healthMessage: 'Watch market moves.',
  borrowApyPercent: 5.2,
  borrowApyLabel: '5.2% variable',
  liquidationPrice: null,
  protocolLabel: 'Powered by Morpho',
  chainId: 8453,
  ...overrides,
})

describe('lombardLoanCardFormat', () => {
  it('maps health status to loan card safety tones', () => {
    assert.equal(mapLombardHealthToLoanSafety('comfortable'), 'ok')
    assert.equal(mapLombardHealthToLoanSafety('monitor'), 'warn')
    assert.equal(mapLombardHealthToLoanSafety('risky'), 'error')
    assert.equal(resolveLombardHealthLabelFr('monitor', 'To monitor'), 'À surveiller')
  })

  it('estimates monthly interest from borrow amount and APY', () => {
    const monthly = estimateLombardMonthlyInterestUsdc([samplePosition()])
    assert.ok(monthly > 0.1)
  })

  it('summarizes total borrowed for the hero', () => {
    const summary = resolveCreditLineSummary([
      samplePosition({ borrowAmount: '25.002204' }),
      samplePosition({ marketId: 'm2', collateralSymbol: 'cbETH', borrowAmount: '15.000427' }),
    ])
    assert.equal(summary.loanCount, 2)
    assert.match(summary.totalBorrowedLabel, /USDC/)
    assert.match(summary.monthlyInterestLabel, /USDC/)
  })
})
