import { after, describe, it } from 'node:test'
import assert from 'node:assert/strict'

;(process.env as Record<string, string | undefined>).NODE_ENV = 'test'
process.env.LEDGITY_LOCAL_SANDBOX_ENABLED = 'true'
process.env.LEDGITY_LOCAL_SANDBOX_YIELD_BPS = '900'
process.env.LEDGITY_LOCAL_SANDBOX_PPS = '1.0578'

import {
  applyLedgitySandboxPps,
  applyLedgitySandboxYield,
  generateSandboxTxHash,
  getSandboxMockVaultCatalog,
  listSandboxMockVaultCatalogs,
} from './mocks/ledgityLocalSandbox'
import { isLedgityLocalSandboxEnabled } from './ledgityLocalSandboxConfig'
import {
  LEDGITY_LYEURC_VAULT,
  LEDGITY_LYUSDC_VAULT,
} from './ledgityConstants'

describe('ledgity local sandbox config', () => {
  it('sandbox enabled in test env', () => {
    assert.equal(isLedgityLocalSandboxEnabled(), true)
  })

  it('production guard blocks sandbox in production', () => {
    const env = process.env as Record<string, string | undefined>
    const previous = env.NODE_ENV
    env.NODE_ENV = 'production'
    try {
      assert.throws(() => isLedgityLocalSandboxEnabled(), /cannot be true in production/)
    } finally {
      env.NODE_ENV = previous
    }
  })
})

describe('ledgity local sandbox vaults', () => {
  it('returns lyUSDC and lyEURC mock catalogs', () => {
    const rows = listSandboxMockVaultCatalogs()
    assert.ok(rows.length >= 2)
    assert.ok(rows.some((row) => row.symbol === 'lyUSDC'))
    assert.ok(rows.some((row) => row.symbol === 'lyEURC'))
  })

  it('mock vault has APY PPS TVL and asset metadata', () => {
    const row = getSandboxMockVaultCatalog(LEDGITY_LYUSDC_VAULT)
    assert.ok(row)
    assert.equal(row?.asset.symbol, 'USDC')
    assert.equal(row?.asset.decimals, 6)
    assert.ok(row?.netApy != null && row.netApy > 0)
    assert.ok(row?.pricePerShare != null && row.pricePerShare > 1)
    assert.ok(row?.tvlUsd != null && row.tvlUsd > 0)
  })

  it('lyEURC vault resolves from catalog', () => {
    const row = getSandboxMockVaultCatalog(LEDGITY_LYEURC_VAULT)
    assert.ok(row)
    assert.equal(row?.asset.symbol, 'EURC')
  })
})

describe('ledgity local sandbox yield', () => {
  it('applyLedgitySandboxPps scales principal by PPS', () => {
    const principal = BigInt(1_000_000)
    const withPps = applyLedgitySandboxPps(principal, 1.0578)
    assert.equal(withPps, BigInt(1_057_800))
  })

  it('applyLedgitySandboxYield adds yield bps on top of PPS', () => {
    const principal = BigInt(1_000_000)
    const withYield = applyLedgitySandboxYield(principal, 900)
    assert.ok(withYield > principal)
  })

  it('generateSandboxTxHash returns valid 0x hash', () => {
    const hash = generateSandboxTxHash()
    assert.match(hash, /^0x[0-9a-f]{64}$/)
  })
})

after(() => {
  delete process.env.LEDGITY_LOCAL_SANDBOX_ENABLED
  delete process.env.LEDGITY_LOCAL_SANDBOX_YIELD_BPS
  delete process.env.LEDGITY_LOCAL_SANDBOX_PPS
})
