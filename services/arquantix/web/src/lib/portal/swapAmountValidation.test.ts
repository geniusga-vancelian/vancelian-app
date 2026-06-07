import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isOnChainBalanceVerified,
  isSwapAmountOverOnChainBalance,
  isSwapAmountOverPrivyBalance,
  isSwapBlockedPendingOnChainVerification,
  resolveLiveSwapSourceBalance,
  resolvePrivySwapSpendableCap,
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

  it('resolveSpendableSwapBalance prefers official swappable_balance', () => {
    assert.equal(
      resolveSpendableSwapBalance({ swappableBalance: 62.64, balance: 176.74, onChainBalance: 62.64 }),
      62.64,
    )
    assert.equal(
      resolveSpendableSwapBalance({ swappableBalance: 0, balance: 176.74 }),
      0,
    )
  })

  it('resolveSpendableSwapBalance falls back to min ledger/on-chain without swappable', () => {
    assert.equal(resolveSpendableSwapBalance({ balance: 1150, onChainBalance: 38 }), 38)
    assert.equal(resolveSpendableSwapBalance({ balance: 10, onChainBalance: 38 }), 10)
    assert.equal(resolveSpendableSwapBalance({ balance: 0, onChainBalance: 38 }), 38)
    assert.equal(resolveSpendableSwapBalance({ balance: 50 }), 50)
  })

  it('isOnChainBalanceVerified requires finite on-chain value or server swappable_balance', () => {
    assert.equal(isOnChainBalanceVerified({ onChainBalance: 0.21 }), true)
    assert.equal(isOnChainBalanceVerified({ onChainBalance: 0 }), true)
    assert.equal(isOnChainBalanceVerified({ swappableBalance: 62.64 }), true)
    assert.equal(isOnChainBalanceVerified({}), false)
    assert.equal(isOnChainBalanceVerified(null), false)
  })

  it('resolvePrivySwapSpendableCap uses min ledger/on-chain when verified', () => {
    const cap = resolvePrivySwapSpendableCap({ balance: 0.211555, onChainBalance: 0.000001 })
    assert.equal(cap.onChainVerified, true)
    assert.equal(cap.spendable, 0.000001)
  })

  it('blocks continue when on-chain verification pending on privy wallet', () => {
    assert.equal(isSwapBlockedPendingOnChainVerification(true, false, false), true)
    assert.equal(isSwapBlockedPendingOnChainVerification(true, true, false), false)
    assert.equal(isSwapBlockedPendingOnChainVerification(false, false, false), false)
  })

  it('rejects amount above verified on-chain balance', () => {
    assert.equal(isSwapAmountOverOnChainBalance(0.21, 0.000001, true), true)
    assert.equal(isSwapAmountOverOnChainBalance(0.000001, 0.21, true), false)
    assert.equal(isSwapAmountOverOnChainBalance(0.21, 0.21, false), false)
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
