import { after, afterEach, before, describe, it, mock } from 'node:test'
import assert from 'node:assert/strict'

process.env.NODE_ENV = 'test'
process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'
process.env.MORPHO_LOCAL_SANDBOX_YIELD_BPS = '450'

import {
  applySandboxYield,
  executeSandboxDirectMorphoOperation,
  fetchSandboxMorphoVaultPosition,
  generateSandboxTxHash,
  getSandboxDependencyHealth,
  getSandboxMockVaultCatalog,
  listSandboxMockVaultCatalogs,
  runSandboxMorphoReconciliationItem,
} from './mocks/morphoLocalSandbox'
import { isMorphoLocalSandboxEnabled } from './morphoLocalSandboxConfig'
import { checkMorphoDependencyHealth } from './morphoVaultMonitoring'
import { MorphoVaultLedgerError } from './morphoVaultLedger'

const STEAKHOUSE = '0xbeef0e0834849acc03f0089f01f4f1eeb06873c9'
const GAUNTLET = '0x050ce30b927da55177a4914ec73480238bad56f0'
const WALLET = '0x00000000000000000000000000000000000101'

describe('morpho local sandbox config', () => {
  it('sandbox enabled in test env', () => {
    assert.equal(isMorphoLocalSandboxEnabled(), true)
  })

  it('production guard blocks sandbox in production', () => {
    const previous = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    try {
      assert.throws(() => isMorphoLocalSandboxEnabled(), /cannot be true in production/)
    } finally {
      process.env.NODE_ENV = previous
    }
  })
})

describe('morpho local sandbox vaults', () => {
  it('returns at least 2 mock vault catalogs', () => {
    const rows = listSandboxMockVaultCatalogs()
    assert.ok(rows.length >= 2)
    assert.ok(rows.some((row) => row.name.includes('Steakhouse')))
    assert.ok(rows.some((row) => row.name.includes('Gauntlet')))
  })

  it('mock vault has APY TVL liquidity USDC chain metadata', () => {
    const row = getSandboxMockVaultCatalog(STEAKHOUSE)
    assert.ok(row)
    assert.equal(row?.asset.symbol, 'USDC')
    assert.equal(row?.asset.decimals, 6)
    assert.ok(row?.netApy != null && row.netApy > 0)
    assert.ok(row?.tvlUsd != null && row.tvlUsd > 0)
    assert.ok(row?.liquidityUsd != null && row.liquidityUsd > 0)
  })
})

describe('morpho local sandbox yield', () => {
  it('applySandboxYield increases principal by configured bps', () => {
    const principal = BigInt(1_000_000)
    const withYield = applySandboxYield(principal, 450)
    assert.equal(withYield, BigInt(1_045_000))
  })

  it('generateSandboxTxHash returns valid 0x hash', () => {
    const hash = generateSandboxTxHash()
    assert.match(hash, /^0x[0-9a-f]{64}$/)
  })
})

describe('morpho local sandbox monitoring', () => {
  it('dependency health is mocked healthy', () => {
    const health = getSandboxDependencyHealth()
    assert.equal(health.morphoGraphql.ok, true)
    assert.equal(health.baseRpc.ok, true)
    assert.equal(health.baseRpc.activeProvider, 'local-sandbox')
  })

  it('checkMorphoDependencyHealth uses sandbox without network', async () => {
    const fetchMock = mock.fn(async () => {
      throw new Error('network should not be called')
    })
    const originalFetch = globalThis.fetch
    globalThis.fetch = fetchMock as typeof fetch
    try {
      const health = await checkMorphoDependencyHealth()
      assert.equal(health.morphoGraphql.ok, true)
      assert.equal(fetchMock.mock.calls.length, 0)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

describe('morpho local sandbox ledger (requires DATABASE_URL)', () => {
  const personId = process.env.ARQUANTIX_MORPHO_SANDBOX_PERSON_ID
  const hasDb = Boolean(process.env.DATABASE_URL && personId)

  before(() => {
    if (!hasDb) {
      console.log('[morphoLocalSandbox.test] skip DB tests — set DATABASE_URL + ARQUANTIX_MORPHO_SANDBOX_PERSON_ID')
    }
  })

  it('sandbox deposit increases position', async (t) => {
    if (!hasDb) return t.skip('DB sandbox person not configured')

    const idempotencyKey = `sandbox-test-deposit-${Date.now()}`
    const prepared = await executeSandboxDirectMorphoOperation({
      personId: personId!,
      vaultAddress: GAUNTLET,
      walletAddress: WALLET,
      operation: 'deposit',
      amountRaw: '10000000',
      assetSymbol: 'USDC',
      assetDecimals: 6,
      idempotencyKey,
    })

    assert.equal(prepared.serverCompleted, true)
    assert.ok(prepared.ledgerEntries.length >= 1)

    const position = await fetchSandboxMorphoVaultPosition({
      personId: personId!,
      vaultAddress: GAUNTLET,
      walletAddress: WALLET,
    })
    assert.ok(position)
    assert.ok(BigInt(position!.assets) >= BigInt(10_000_000))
  })

  it('sandbox withdraw > balance rejected', async (t) => {
    if (!hasDb) return t.skip('DB sandbox person not configured')

    await assert.rejects(
      () =>
        executeSandboxDirectMorphoOperation({
          personId: personId!,
          vaultAddress: GAUNTLET,
          walletAddress: WALLET,
          operation: 'withdraw',
          amountRaw: '999999999999',
          assetSymbol: 'USDC',
          assetDecimals: 6,
          idempotencyKey: `sandbox-test-withdraw-overflow-${Date.now()}`,
        }),
      (error: unknown) => {
        assert.ok(error instanceof MorphoVaultLedgerError)
        assert.equal(error.code, 'morpho.withdraw_exceeds_position')
        return true
      },
    )
  })

  it('sandbox reconciliation matched', async (t) => {
    if (!hasDb) return t.skip('DB sandbox person not configured')

    const item = await runSandboxMorphoReconciliationItem({
      personId: personId!,
      vaultAddress: GAUNTLET,
      walletAddress: WALLET,
    })
    assert.equal(item.status, 'matched')
    assert.equal(item.ledgerAssetsRaw, item.onchainAssetsRaw)
  })
})

afterEach(() => {
  process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'
})

after(() => {
  delete process.env.MORPHO_LOCAL_SANDBOX_ENABLED
})
