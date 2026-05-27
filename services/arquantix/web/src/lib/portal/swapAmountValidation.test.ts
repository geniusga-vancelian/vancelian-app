import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { isSwapAmountOverPrivyBalance } from '@/lib/portal/swapAmountValidation'

describe('swapAmountValidation', () => {
  it('blocks positive amount when source balance is zero or unknown', () => {
    assert.equal(isSwapAmountOverPrivyBalance(60, 0), true)
    assert.equal(isSwapAmountOverPrivyBalance(1, -1), true)
  })

  it('blocks amount above known balance', () => {
    assert.equal(isSwapAmountOverPrivyBalance(60, 33.19), true)
    assert.equal(isSwapAmountOverPrivyBalance(33.19, 33.19), false)
    assert.equal(isSwapAmountOverPrivyBalance(10, 33.19), false)
  })

  it('ignores invalid or empty amounts', () => {
    assert.equal(isSwapAmountOverPrivyBalance(0, 100), false)
    assert.equal(isSwapAmountOverPrivyBalance(Number.NaN, 100), false)
  })
})
