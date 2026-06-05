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

  it('uses portal balance when on-chain read is still zero', () => {
    const raw = resolveEffectiveWalletCollateralRaw({
      onChainRaw: BigInt(0),
      portalBalanceHuman: '0.0006',
      decimals: 8,
    })
    assert.equal(raw, BigInt(60_000))
  })

  it('never inflates with portal balance when on-chain is already non-zero', () => {
    const onChainRaw = BigInt('3244820948372523')
    const raw = resolveEffectiveWalletCollateralRaw({
      onChainRaw,
      portalBalanceHuman: '0.05',
      decimals: 18,
    })
    assert.equal(raw, onChainRaw)
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
