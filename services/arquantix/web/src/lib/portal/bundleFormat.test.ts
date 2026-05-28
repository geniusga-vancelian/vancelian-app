import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  displayBundleAssetSymbol,
  formatBundleTargetWeight,
  formatBundleUsdcAmount,
  normalizeBundleAssetSymbol,
} from '@/lib/portal/bundleFormat'

describe('bundleFormat', () => {
  it('normalizes legacy BTC/ETH to CBBTC/CBETH', () => {
    assert.equal(normalizeBundleAssetSymbol('BTC'), 'CBBTC')
    assert.equal(normalizeBundleAssetSymbol('ETH'), 'CBETH')
    assert.equal(normalizeBundleAssetSymbol('LINK'), 'LINK')
  })

  it('displays cbBTC and cbETH labels', () => {
    assert.equal(displayBundleAssetSymbol('BTC'), 'cbBTC')
    assert.equal(displayBundleAssetSymbol('CBBTC'), 'cbBTC')
    assert.equal(displayBundleAssetSymbol('ETH'), 'cbETH')
    assert.equal(displayBundleAssetSymbol('LINK'), 'LINK')
  })

  it('formats target weights as percentages', () => {
    assert.equal(formatBundleTargetWeight('0.5'), '50 %')
    assert.equal(formatBundleTargetWeight('0.066667'), '6.7 %')
  })

  it('formats USDC leg amounts', () => {
    assert.equal(formatBundleUsdcAmount('25'), '25.00')
    assert.equal(formatBundleUsdcAmount('3.333333'), '3.33')
  })
})
