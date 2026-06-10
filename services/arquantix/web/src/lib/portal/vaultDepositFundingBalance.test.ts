import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'

import {
  buildLockedInvestSource,
  resolveVaultDepositFundingBalance,
  VAULT_DEPOSIT_FUNDING_ASSET,
} from '@/lib/portal/portalInvestFlowFormat'

describe('vault deposit funding balance', () => {
  const prevEuroEnabled = process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED

  afterEach(() => {
    if (prevEuroEnabled === undefined) delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
    else process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED = prevEuroEnabled
  })

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
  })

  it('uses tradingAvailableUsdc when present', () => {
    const balance = resolveVaultDepositFundingBalance({
      tradingAvailableUsdc: 62.641746,
      positions: [{ asset: 'USDC', chainId: 8453, balance: 0 }],
    })
    assert.equal(balance, 62.641746)
  })

  it('buildLockedInvestSource for EURC vault keeps EURC template when euro hidden', () => {
    const source = buildLockedInvestSource('EURC', 12.5)
    assert.equal(source.key, 'eur')
    assert.equal(source.short, 'EURC')
    assert.equal(source.balance, 12.5)
    assert.match(source.balanceLabel, /12\.50 EURC/)
  })

  it('vault deposit funding asset is USDC', () => {
    assert.equal(VAULT_DEPOSIT_FUNDING_ASSET, 'USDC')
    const source = buildLockedInvestSource(VAULT_DEPOSIT_FUNDING_ASSET, 10)
    assert.equal(source.key, 'usdc')
    assert.match(source.balanceLabel, /10\.00 USDC/)
  })
})
