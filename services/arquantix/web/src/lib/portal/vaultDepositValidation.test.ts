import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertVaultDepositWithinTradingAvailable,
  resolveTradingAvailableUsdcFromDirectPayload,
  VaultDepositLimitError,
} from '@/lib/portal/vaultDepositValidation'
import { resolveVaultDepositUsdcBalance } from '@/lib/portal/portalInvestFlowFormat'

describe('resolveVaultDepositUsdcBalance', () => {
  it('prefers trading_available over merged balance and on-chain', () => {
    const balance = resolveVaultDepositUsdcBalance([
      {
        asset: 'USDC',
        chainId: 8453,
        balance: 183.11,
        availableBalance: 183.11,
        platformBalance: 2.11,
        tradingAvailable: 2.111143,
      },
    ])
    assert.equal(balance, 2.111143)
  })

  it('falls back to platformBalance when trading_available absent', () => {
    const balance = resolveVaultDepositUsdcBalance([
      {
        asset: 'USDC',
        chainId: 8453,
        balance: 50,
        platformBalance: 2.11,
      },
    ])
    assert.equal(balance, 2.11)
  })

  it('returns zero instead of merged balance when scope fields missing', () => {
    const balance = resolveVaultDepositUsdcBalance([
      {
        asset: 'USDC',
        chainId: 8453,
        balance: 183.11,
        availableBalance: 183.11,
      },
    ])
    assert.equal(balance, 0)
  })
})

describe('resolveTradingAvailableUsdcFromDirectPayload', () => {
  it('reads trading_available from direct API payload', () => {
    const value = resolveTradingAvailableUsdcFromDirectPayload({
      positions: [
        {
          asset: 'USDC',
          chain_id: 8453,
          balance: '183.11',
          platform_balance: '2.11',
          trading_available: '2.111143',
        },
      ],
    })
    assert.equal(value, 2.111143)
  })
})

describe('assertVaultDepositWithinTradingAvailable', () => {
  it('allows deposit within trading_available', () => {
    assert.doesNotThrow(() =>
      assertVaultDepositWithinTradingAvailable({ amount: 1, tradingAvailable: 2.11 }),
    )
  })

  it('rejects deposit above trading_available', () => {
    assert.throws(
      () => assertVaultDepositWithinTradingAvailable({ amount: 10, tradingAvailable: 2.11 }),
      (error: unknown) => {
        assert.ok(error instanceof VaultDepositLimitError)
        assert.equal(error.available, 2.11)
        assert.equal(error.requested, 10)
        return true
      },
    )
  })
})
