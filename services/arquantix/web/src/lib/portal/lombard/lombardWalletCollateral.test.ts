import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  resolveEffectiveWalletCollateralRaw,
  resolvePortalCollateralBalanceHuman,
} from '@/lib/portal/lombard/lombardWalletCollateral'

describe('lombardWalletCollateral', () => {
  it('prefers on-chain balance when portal balance is absent', () => {
    const raw = resolveEffectiveWalletCollateralRaw({
      onChainRaw: BigInt(60_000),
      portalBalanceHuman: null,
      decimals: 8,
    })
    assert.equal(raw, BigInt(60_000))
  })

  it('uses portal balance when higher than on-chain read', () => {
    const raw = resolveEffectiveWalletCollateralRaw({
      onChainRaw: BigInt(0),
      portalBalanceHuman: '0.0006',
      decimals: 8,
    })
    assert.equal(raw, BigInt(60_000))
  })

  it('resolvePortalCollateralBalanceHuman prefers onChainBalance', () => {
    assert.equal(
      resolvePortalCollateralBalanceHuman({
        balance: 1,
        availableBalance: 0.5,
        onChainBalance: 0.0006,
      }),
      0.0006,
    )
  })
})
