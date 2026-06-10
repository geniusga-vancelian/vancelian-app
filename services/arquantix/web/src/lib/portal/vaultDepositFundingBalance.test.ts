import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'

import {
  buildLockedInvestSource,
  resolveVaultDepositBalanceForAsset,
} from '@/lib/portal/portalInvestFlowFormat'
import { resolveTradingAvailableEurcFromDirectPayload } from '@/lib/portal/vaultDepositValidation'

describe('vault deposit balance by vault asset', () => {
  const prevEuroEnabled = process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED

  afterEach(() => {
    if (prevEuroEnabled === undefined) delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
    else process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED = prevEuroEnabled
  })

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
  })

  it('uses USDC trading_available for USDC vaults', () => {
    const balance = resolveVaultDepositBalanceForAsset('USDC', {
      tradingAvailableUsdc: 62.641746,
      positions: [{ asset: 'USDC', chainId: 8453, balance: 0 }],
    })
    assert.equal(balance, 62.641746)
  })

  it('uses EURC trading_available for EURC vaults', () => {
    const balance = resolveVaultDepositBalanceForAsset('EURC', {
      tradingAvailableEurc: 18.5,
      positions: [{ asset: 'EURC', chainId: 8453, balance: 0 }],
    })
    assert.equal(balance, 18.5)
  })

  it('reads EURC trading_available from direct API payload', () => {
    const value = resolveTradingAvailableEurcFromDirectPayload({
      positions: [
        {
          asset: 'EURC',
          chain_id: 8453,
          balance: '0',
          platform_balance: '0',
          trading_available: '18.500000',
        },
      ],
    })
    assert.equal(value, 18.5)
  })

  it('buildLockedInvestSource for EURC vault keeps EURC template when euro hidden', () => {
    const source = buildLockedInvestSource('EURC', 12.5)
    assert.equal(source.key, 'eur')
    assert.equal(source.short, 'EURC')
    assert.equal(source.balance, 12.5)
    assert.match(source.balanceLabel, /12\.50 EURC/)
  })

  it('buildLockedInvestSource for USDC vault keeps USDC template', () => {
    const source = buildLockedInvestSource('USDC', 10)
    assert.equal(source.key, 'usdc')
    assert.match(source.balanceLabel, /10\.00 USDC/)
  })
})
