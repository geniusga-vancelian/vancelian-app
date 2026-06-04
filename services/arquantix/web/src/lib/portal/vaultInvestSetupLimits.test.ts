import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  resolveEffectiveVaultDepositMax,
  validateVaultDepositSetupAmount,
  validateVaultWithdrawSetupAmount,
  vaultSetupExceedsMaxWarning,
} from '@/lib/portal/vaultInvestSetupLimits'

const limits = {
  minDepositUsdc: 10,
  maxDepositUsdc: 100,
  maxUserExposureUsdc: 500,
}

describe('vaultInvestSetupLimits', () => {
  it('caps deposit max by wallet, per-tx limit, and exposure headroom', () => {
    assert.equal(
      resolveEffectiveVaultDepositMax({ walletUsdc: 50, vaultPositionUsdc: 480, limits }),
      20,
    )
    assert.equal(
      resolveEffectiveVaultDepositMax({ walletUsdc: 200, vaultPositionUsdc: 0, limits }),
      100,
    )
  })

  it('rejects amount above trading-available wallet balance', () => {
    const message = validateVaultDepositSetupAmount({
      amount: 10,
      walletUsdc: 5,
      vaultPositionUsdc: 0,
      limits,
    })
    assert.match(message ?? '', /maximum disponible.*5/i)
  })

  it('rejects amount above per-tx beta limit', () => {
    const message = validateVaultDepositSetupAmount({
      amount: 150,
      walletUsdc: 200,
      vaultPositionUsdc: 0,
      limits,
    })
    assert.match(message ?? '', /maximum par opération.*100/i)
  })

  it('rejects withdraw above vault balance with max hint', () => {
    const message = validateVaultWithdrawSetupAmount({
      amount: 50,
      vaultBalanceUsdc: 12.5,
      assetSymbol: 'USDC',
    })
    assert.match(message ?? '', /maximum retirable.*12,5.*USDC/i)
  })

  it('returns null for withdraw within vault balance', () => {
    assert.equal(
      validateVaultWithdrawSetupAmount({
        amount: 10,
        vaultBalanceUsdc: 12.5,
        assetSymbol: 'USDC',
      }),
      null,
    )
  })

  it('warns when withdraw amount exceeds vault balance', () => {
    const message = vaultSetupExceedsMaxWarning({
      amount: 10,
      maxAmount: 5.23,
      assetSymbol: 'USDC',
      kind: 'withdraw',
    })
    assert.match(message ?? '', /dépasse le maximum retirable/i)
    assert.match(message ?? '', /5,23.*USDC/)
  })
})
