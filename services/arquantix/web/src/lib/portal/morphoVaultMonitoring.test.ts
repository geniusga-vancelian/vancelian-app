import { describe, it, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildMorphoMonitoringAlerts,
  compareMorphoReconciliationAssets,
  computeMorphoGlobalStatus,
  isSignificantMismatchDelta,
} from './morphoVaultMonitoring'
import {
  getMorphoReconciliationToleranceRaw,
  getMorphoAlertMismatchToleranceRaw,
} from './morphoReconciliationConfig'

describe('morphoReconciliationConfig', () => {
  let prevTolerance: string | undefined
  let prevAlert: string | undefined

  beforeEach(() => {
    prevTolerance = process.env.MORPHO_RECONCILIATION_TOLERANCE_RAW
    prevAlert = process.env.MORPHO_ALERT_MISMATCH_TOLERANCE_RAW
  })

  afterEach(() => {
    if (prevTolerance === undefined) delete process.env.MORPHO_RECONCILIATION_TOLERANCE_RAW
    else process.env.MORPHO_RECONCILIATION_TOLERANCE_RAW = prevTolerance
    if (prevAlert === undefined) delete process.env.MORPHO_ALERT_MISMATCH_TOLERANCE_RAW
    else process.env.MORPHO_ALERT_MISMATCH_TOLERANCE_RAW = prevAlert
  })

  it('utilise tolérance configurable MORPHO_RECONCILIATION_TOLERANCE_RAW', () => {
    process.env.MORPHO_RECONCILIATION_TOLERANCE_RAW = '10'
    assert.equal(getMorphoReconciliationToleranceRaw(), BigInt(10))
    assert.equal(
      compareMorphoReconciliationAssets({
        ledgerAssetsRaw: '1000000',
        onchainAssetsRaw: '1000005',
      }),
      'matched',
    )
    assert.equal(
      compareMorphoReconciliationAssets({
        ledgerAssetsRaw: '1000000',
        onchainAssetsRaw: '1000100',
      }),
      'mismatch',
    )
  })

  it('alerte mismatch significatif > 1 USDC par défaut', () => {
    assert.equal(isSignificantMismatchDelta('1000001'), true)
    assert.equal(isSignificantMismatchDelta('50'), false)
    process.env.MORPHO_ALERT_MISMATCH_TOLERANCE_RAW = '1000000'
    assert.equal(getMorphoAlertMismatchToleranceRaw(), BigInt(1_000_000))
  })
})

describe('morphoVaultMonitoring alerts', () => {
  const healthyDeps = {
    morphoGraphql: { ok: true, latencyMs: 120 },
    baseRpc: {
      ok: true,
      latencyMs: 80,
      activeProvider: 'alchemy',
      usedFallback: false,
      publicRpcAsPrimary: false,
      providers: [{ label: 'alchemy', ok: true, latencyMs: 80, isPublic: false }],
    },
  }

  it('retourne Healthy sans alerte', () => {
    const alerts = buildMorphoMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      inactiveRegistryVaultsCount: 0,
      dependencyHealth: healthyDeps,
    })
    assert.equal(computeMorphoGlobalStatus(alerts), 'healthy')
  })

  it('retourne Critical si GraphQL ou RPC down', () => {
    const alerts = buildMorphoMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      inactiveRegistryVaultsCount: 0,
      dependencyHealth: {
        morphoGraphql: { ok: false, error: 'timeout' },
        baseRpc: { ok: true },
      },
    })
    assert.equal(computeMorphoGlobalStatus(alerts), 'critical')
    assert.ok(alerts.some((a) => a.code === 'morpho_graphql_unavailable'))
  })

  it('retourne Warning si pending tx stale', () => {
    const alerts = buildMorphoMonitoringAlerts({
      pendingTransactionsCount: 1,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      inactiveRegistryVaultsCount: 0,
      dependencyHealth: healthyDeps,
    })
    assert.equal(computeMorphoGlobalStatus(alerts), 'warning')
    assert.ok(alerts.some((a) => a.code === 'pending_tx_stale'))
  })

  it('retourne Critical si mismatch > 1 USDC', () => {
    const alerts = buildMorphoMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 1,
      significantMismatchCount: 1,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      inactiveRegistryVaultsCount: 0,
      dependencyHealth: healthyDeps,
    })
    assert.equal(computeMorphoGlobalStatus(alerts), 'critical')
  })
})
