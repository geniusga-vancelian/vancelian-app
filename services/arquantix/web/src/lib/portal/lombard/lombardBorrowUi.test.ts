import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  estimateLombardGuaranteeDisplay,
  normalizeLombardBorrowAmountForApi,
  parseBorrowAmountInput,
} from '@/lib/portal/lombard/lombardBorrowUi'
import { lombardQuoteSchema } from '@/lib/portal/lombard/lombardValidation'

describe('lombardBorrowUi amount parsing', () => {
  it('parses French spaced thousands', () => {
    assert.equal(parseBorrowAmountInput('3 440'), 3440)
    assert.equal(parseBorrowAmountInput('3\u00a0440,50'), 3440.5)
  })

  it('normalizes API borrow amount without spaces', () => {
    assert.equal(normalizeLombardBorrowAmountForApi('3 440'), '3440')
    assert.equal(normalizeLombardBorrowAmountForApi('100,5'), '100.5')
  })

  it('accepts spaced amount in lombardQuoteSchema', () => {
    const parsed = lombardQuoteSchema.parse({
      collateral: 'cbBTC',
      borrowAmount: '3 440',
      walletAddress: '0x0000000000000000000000000000000000000001',
      targetLtvPercent: '43',
    })
    assert.equal(parsed.borrowAmount, '3440')
  })

  it('estimates guarantee from borrow amount and LTV', () => {
    const estimate = estimateLombardGuaranteeDisplay({
      borrowAmountUsd: 3440,
      targetLtvPercent: 43,
      collateral: 'cbBTC',
      collateralPriceUsd: 100_000,
    })
    assert.ok(estimate)
    assert.equal(estimate.collateral, 'cbBTC')
    assert.ok(parseBorrowAmountInput(estimate.guaranteeAmount) > 0)
  })
})
