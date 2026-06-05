import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatSwapMinAmountError,
  isSwapAmountBelowCatalogMin,
  parseSwapCatalogMinAmount,
} from '@/lib/portal/swapMinAmount'

describe('swapMinAmount', () => {
  it('parseSwapCatalogMinAmount accepts positive catalog values', () => {
    assert.equal(parseSwapCatalogMinAmount('1'), 1)
    assert.equal(parseSwapCatalogMinAmount('5'), 5)
    assert.equal(parseSwapCatalogMinAmount('0.00001'), 0.00001)
  })

  it('isSwapAmountBelowCatalogMin mirrors backend threshold', () => {
    assert.equal(isSwapAmountBelowCatalogMin(1, '1'), false)
    assert.equal(isSwapAmountBelowCatalogMin(0.99, '1'), true)
    assert.equal(isSwapAmountBelowCatalogMin(4.99, '5'), true)
    assert.equal(isSwapAmountBelowCatalogMin(5, '5'), false)
  })

  it('formatSwapMinAmountError matches API message', () => {
    assert.equal(formatSwapMinAmountError('USDC', '1'), 'Montant minimum : 1 USDC')
  })
})
