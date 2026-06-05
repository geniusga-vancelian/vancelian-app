import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  BUNDLE_MIN_FUNDING_USDC,
  formatBundleMinFundingError,
  isBundleFundingBelowMin,
  minimumBundleFundingAmount,
} from '@/lib/portal/bundleMinFunding'

describe('bundleMinFunding', () => {
  it('minimum USDC/EURC is 20', () => {
    assert.equal(BUNDLE_MIN_FUNDING_USDC, 20)
    assert.equal(minimumBundleFundingAmount('USDC'), 20)
    assert.equal(minimumBundleFundingAmount('EURC'), 20)
  })

  it('isBundleFundingBelowMin mirrors backend threshold', () => {
    assert.equal(isBundleFundingBelowMin(20, 'USDC'), false)
    assert.equal(isBundleFundingBelowMin(19.99, 'USDC'), true)
    assert.equal(isBundleFundingBelowMin(20, 'EURC'), false)
  })

  it('formatBundleMinFundingError matches API message', () => {
    assert.equal(formatBundleMinFundingError('USDC'), 'Montant minimum : 20 USDC')
  })
})
