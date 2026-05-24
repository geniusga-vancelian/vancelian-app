/**
 * Tests HTTP / API Morpho — logique monitoring + intégration DB optionnelle.
 *
 * Unit : monitoring, réconciliation, config (toujours).
 * DB   : ARQUANTIX_MORPHO_INTEGRATION=1 + DATABASE_URL
 */
import { describe, it, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { PrismaClient } from '@prisma/client'

import { getMorphoMonitoringSnapshot, runMorphoVaultReconciliation } from './morphoVaultReconciliation'
import { syncMorphoVaultRegistryFromConfigs } from './morphoVaultRegistrySync'

const runDbIntegration =
  process.env.ARQUANTIX_MORPHO_INTEGRATION === '1' && Boolean(process.env.DATABASE_URL)

describe('morpho HTTP API contracts (unit)', () => {
  it('monitoring snapshot inclut globalStatus, alerts et beta', async () => {
    const snapshot = await getMorphoMonitoringSnapshot({ pendingMinutes: 15 })
    assert.ok(['healthy', 'warning', 'critical'].includes(snapshot.globalStatus))
    assert.ok(Array.isArray(snapshot.alerts))
    assert.ok(snapshot.dependencyHealth.morphoGraphql)
    assert.ok(snapshot.dependencyHealth.baseRpc)
    assert.ok(Array.isArray(snapshot.activeVaults))
    assert.ok(Array.isArray(snapshot.pendingTransactions))
    assert.ok(snapshot.beta)
    assert.equal(typeof snapshot.beta.betaActiveUsersCount, 'number')
    assert.equal(typeof snapshot.beta.totalDepositedUsdc, 'number')
  })

  it('registry sync retourne un résumé structuré', async () => {
    const result = await syncMorphoVaultRegistryFromConfigs()
    assert.ok(typeof result.scanned === 'number')
    assert.ok(typeof result.upserted === 'number')
    assert.ok(typeof result.syncedAt === 'string')
  })
})

;(runDbIntegration ? describe : describe.skip)('morpho HTTP API (DB integration)', () => {
  const prisma = new PrismaClient()

  afterEach(async () => {
    await prisma.$disconnect()
  })

  it('reconciliation run persiste un run en DB', async () => {
    const summary = await runMorphoVaultReconciliation()
    assert.ok(summary.runId)
    const run = await prisma.morphoVaultReconciliationRun.findUnique({
      where: { id: summary.runId },
    })
    assert.ok(run)
    assert.ok(run?.finishedAt)
  })

  it('history query shape — transactions par person_id', async () => {
    const sample = await prisma.onchainVaultTransaction.findFirst({
      select: { personId: true },
    })
    if (!sample) return
    const rows = await prisma.onchainVaultTransaction.findMany({
      where: { personId: sample.personId },
      take: 5,
      orderBy: { createdAt: 'desc' },
    })
    assert.ok(Array.isArray(rows))
  })

  it('prepare idempotency unique constraint existe en DB', async () => {
    const indexes = await prisma.$queryRaw<Array<{ indexname: string }>>`
      SELECT indexname FROM pg_indexes
      WHERE tablename = 'onchain_vault_transactions'
      AND indexname LIKE '%idempotency%'
    `
    assert.ok(indexes.length > 0)
  })
})

describe('portal morpho route payloads (schema)', () => {
  it('prepare body requiert idempotency_key', async () => {
    const { idempotencyKeySchema } = await import('./morphoVaultValidation')
    assert.throws(() => idempotencyKeySchema.parse('abc'))
    assert.equal(idempotencyKeySchema.parse('key-12345678'), 'key-12345678')
  })

  it('position response inclut yieldSyncStatus', async () => {
    const { mapMorphoVaultPosition } = await import('./morphoVaultFormat')
    const position = mapMorphoVaultPosition(
      {
        asset: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', symbol: 'USDC', decimals: 6 },
        assets: '1000000',
        shares: '900000',
        assetsUsd: 1,
      },
      '0xvault',
      { costBasisUnknown: true },
    )
    assert.equal(position.yieldSyncStatus, 'pending')
    assert.match(position.earnedYieldDisplay, /synchronisation/)
  })
})
