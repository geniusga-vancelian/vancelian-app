import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatVaultDepositLimitsHint,
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

  it('allows deposit below former min when minDepositUsdc is 0', () => {
    assert.equal(
      validateVaultDepositSetupAmount({
        amount: 1,
        walletUsdc: 50,
        vaultPositionUsdc: 0,
        limits: { ...limits, minDepositUsdc: 0 },
      }),
      null,
    )
  })

  it('returns null limits hint when all beta caps are disabled (0)', () => {
    assert.equal(
      formatVaultDepositLimitsHint({
        minDepositUsdc: 0,
        maxDepositUsdc: 0,
        maxUserExposureUsdc: 0,
      }),
      null,
    )
  })

  it('omits min from limits hint when minDepositUsdc is 0', () => {
    const hint = formatVaultDepositLimitsHint({ ...limits, minDepositUsdc: 0 })
    assert.ok(hint)
    assert.doesNotMatch(hint, /min\./i)
    assert.match(hint, /max\./i)
  })

  it('allows deposit above former per-tx max when maxDepositUsdc is 0', () => {
    assert.equal(
      validateVaultDepositSetupAmount({
        amount: 150,
        walletUsdc: 200,
        vaultPositionUsdc: 0,
        limits: { ...limits, maxDepositUsdc: 0, maxUserExposureUsdc: 0 },
      }),
      null,
    )
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
