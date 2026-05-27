import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isLombardWalletCollateralAsset,
  lombardGuaranteeTagline,
  normalizeLombardCollateralSymbol,
} from '@/lib/portal/lombard/lombardWalletAsset'

describe('lombardWalletAsset', () => {
  it('normalizes wallet tickers', () => {
    assert.equal(normalizeLombardCollateralSymbol('CBBTC'), 'cbBTC')
    assert.equal(normalizeLombardCollateralSymbol('CBETH'), 'cbETH')
    assert.equal(normalizeLombardCollateralSymbol('cbETH'), 'cbETH')
  })

  it('detects eligible assets', () => {
    assert.equal(isLombardWalletCollateralAsset('CBBTC'), true)
    assert.equal(isLombardWalletCollateralAsset('USDC'), false)
  })

  it('taglines', () => {
    assert.match(lombardGuaranteeTagline('cbBTC'), /Bitcoin/)
    assert.match(lombardGuaranteeTagline('cbETH'), /Ethereum/)
  })
})
