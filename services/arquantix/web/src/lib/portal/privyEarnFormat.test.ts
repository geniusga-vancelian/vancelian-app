import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { formatEarnApyFromBps, formatEarnTokenAmount, mapPrivyEarnVaultPosition } from './privyEarnFormat'

describe('formatEarnApyFromBps', () => {
  it('convertit les basis points en pourcentage', () => {
    assert.equal(formatEarnApyFromBps(500), '5.00%')
    assert.equal(formatEarnApyFromBps(null), '—')
  })
})

describe('formatEarnTokenAmount', () => {
  it('formate les montants USDC 6 décimales', () => {
    assert.equal(formatEarnTokenAmount('1500000', 6), '1.5')
    assert.equal(formatEarnTokenAmount('1000000', 6), '1')
  })
})

describe('mapPrivyEarnVaultPosition', () => {
  it('calcule le rendement affiché', () => {
    const position = mapPrivyEarnVaultPosition(
      {
        asset: { address: '0x', symbol: 'usdc', decimals: 6 },
        total_deposited: '1000000',
        total_withdrawn: '0',
        assets_in_vault: '1050000',
        shares_in_vault: '1',
      },
      'vault-1',
    )
    assert.equal(position.assetsInVaultDisplay, '1.05 USDC')
    assert.equal(position.earnedYieldDisplay, '0.05 USDC')
  })
})
