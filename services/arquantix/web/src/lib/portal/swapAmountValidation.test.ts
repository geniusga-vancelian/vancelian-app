import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isSwapAmountOverPrivyBalance,
  resolveLiveSwapSourceBalance,
  resolveSpendableSwapBalance,
} from '@/lib/portal/swapAmountValidation'

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

  it('resolveSpendableSwapBalance prefers min ledger/on-chain', () => {
    assert.equal(resolveSpendableSwapBalance({ balance: 1150, onChainBalance: 38 }), 38)
    assert.equal(resolveSpendableSwapBalance({ balance: 10, onChainBalance: 38 }), 10)
    assert.equal(resolveSpendableSwapBalance({ balance: 0, onChainBalance: 38 }), 38)
    assert.equal(resolveSpendableSwapBalance({ balance: 50 }), 50)
  })

  it('resolveLiveSwapSourceBalance reads position and falls back when missing', () => {
    const positions = [
      { asset: 'USDC', balance: 120, onChainBalance: 100 },
      { asset: 'ETH', balance: 2 },
    ]
    assert.equal(resolveLiveSwapSourceBalance('USDC', positions, 0), 100)
    assert.equal(resolveLiveSwapSourceBalance('usdc', positions, 0), 100)
    assert.equal(resolveLiveSwapSourceBalance('CBBTC', positions, 0), 0)
    assert.equal(resolveLiveSwapSourceBalance('CBBTC', positions, 42), 42)
  })
})
