import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { buildLedgityLedgerMetadata, readLedgityPpsFromLedgerMetadata } from '@/lib/portal/ledgity/ledgityLedgerMetadata'
import { LEDGITY_LYUSDC_VAULT } from '@/lib/portal/ledgity/ledgityConstants'
import {
  buildLedgityMonitoringAlerts,
  compareLedgityReconciliationAssets,
  computeLedgityGlobalStatus,
  isLedgityLiquidityDeferred,
  isLedgitySandboxEnabledInProduction,
} from '@/lib/portal/ledgity/ledgityVaultMonitoring'
import { LedgityVaultLiquidityError } from '@/lib/portal/ledgity/ledgityVaultLiquidity'

describe('ledgityVaultMonitoring', () => {
  it('compareLedgityReconciliationAssets returns matched within tolerance', () => {
    assert.equal(
      compareLedgityReconciliationAssets({ ledgerAssetsRaw: '100', onchainAssetsRaw: '105' }),
      'matched',
    )
  })

  it('compareLedgityReconciliationAssets returns mismatch beyond tolerance', () => {
    assert.equal(
      compareLedgityReconciliationAssets({ ledgerAssetsRaw: '100', onchainAssetsRaw: '200', toleranceRaw: BigInt(10) }),
      'mismatch',
    )
  })

  it('computeLedgityGlobalStatus is healthy without alerts', () => {
    assert.equal(computeLedgityGlobalStatus([]), 'healthy')
  })

  it('computeLedgityGlobalStatus is critical when rpc unavailable', () => {
    const alerts = buildLedgityMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      ppsUnavailableCount: 0,
      liquidityWarningCount: 0,
      vaultPausedCount: 0,
      withdrawalsPausedCount: 0,
      dependencyHealth: {
        baseRpc: { ok: false, error: 'timeout' },
      },
      sandboxEnabledInProd: false,
    })
    assert.equal(computeLedgityGlobalStatus(alerts), 'critical')
    assert.ok(alerts.some((row) => row.code === 'rpc_unavailable'))
  })

  it('buildLedgityMonitoringAlerts flags pps_unavailable', () => {
    const alerts = buildLedgityMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      ppsUnavailableCount: 2,
      liquidityWarningCount: 0,
      vaultPausedCount: 0,
      withdrawalsPausedCount: 0,
      dependencyHealth: { baseRpc: { ok: true } },
      sandboxEnabledInProd: false,
    })
    assert.ok(alerts.some((row) => row.code === 'pps_unavailable'))
  })

  it('buildLedgityMonitoringAlerts flags liquidity_low', () => {
    const alerts = buildLedgityMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      ppsUnavailableCount: 0,
      liquidityWarningCount: 1,
      vaultPausedCount: 0,
      withdrawalsPausedCount: 0,
      dependencyHealth: { baseRpc: { ok: true } },
      sandboxEnabledInProd: false,
    })
    assert.ok(alerts.some((row) => row.code === 'liquidity_low'))
  })

  it('buildLedgityMonitoringAlerts flags sandbox_enabled_in_prod as critical', () => {
    const alerts = buildLedgityMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      ppsUnavailableCount: 0,
      liquidityWarningCount: 0,
      vaultPausedCount: 0,
      withdrawalsPausedCount: 0,
      dependencyHealth: { baseRpc: { ok: true } },
      sandboxEnabledInProd: true,
    })
    assert.equal(computeLedgityGlobalStatus(alerts), 'critical')
    assert.ok(alerts.some((row) => row.code === 'sandbox_enabled_in_prod'))
  })

  it('isLedgityLiquidityDeferred when maxWithdraw below position', () => {
    assert.equal(
      isLedgityLiquidityDeferred({
        maxWithdrawRaw: BigInt(50),
        onchainAssetsRaw: BigInt(100),
        toleranceRaw: BigInt(10),
      }),
      true,
    )
  })

  it('LedgityVaultLiquidityError exposes business code', () => {
    const error = new LedgityVaultLiquidityError()
    assert.equal(error.code, 'ledgity.withdraw_liquidity_insufficient')
    assert.match(error.message, /retrait instantané/)
  })

  it('monitoring Healthy sandbox when dependency ok and no alerts', () => {
    const alerts = buildLedgityMonitoringAlerts({
      pendingTransactionsCount: 0,
      pendingThresholdMinutes: 15,
      mismatchCount: 0,
      significantMismatchCount: 0,
      missingOnchainCount: 0,
      missingLedgerCount: 0,
      ppsUnavailableCount: 0,
      liquidityWarningCount: 0,
      vaultPausedCount: 0,
      withdrawalsPausedCount: 0,
      dependencyHealth: { baseRpc: { ok: true, activeProvider: 'local-sandbox' } },
      sandboxEnabledInProd: false,
    })
    assert.equal(computeLedgityGlobalStatus(alerts), 'healthy')
  })

  it('isLedgitySandboxEnabledInProduction respects env', () => {
    const previousNodeEnv = process.env.NODE_ENV
    const previousSandbox = process.env.LEDGITY_LOCAL_SANDBOX_ENABLED
    process.env.NODE_ENV = 'production'
    process.env.LEDGITY_LOCAL_SANDBOX_ENABLED = 'true'
    assert.equal(isLedgitySandboxEnabledInProduction(), true)
    process.env.NODE_ENV = previousNodeEnv
    process.env.LEDGITY_LOCAL_SANDBOX_ENABLED = previousSandbox
  })
})

describe('ledgityLedgerMetadata', () => {
  it('buildLedgityLedgerMetadata includes protocol and pps_at_tx', () => {
    const metadata = buildLedgityLedgerMetadata({
      vaultAddress: LEDGITY_LYUSDC_VAULT,
      assetSymbol: 'USDC',
      walletSource: { wallet_source: 'external_evm', wallet_provider: 'metamask' },
      ppsAtTx: '1.0578',
    }) as Record<string, unknown>

    assert.equal(metadata.protocol, 'ledgity')
    assert.equal(metadata.share_symbol, 'lyUSDC')
    assert.equal(metadata.asset_symbol, 'USDC')
    assert.equal(metadata.wallet_source, 'external_evm')
    assert.equal(metadata.pps_at_tx, '1.0578')
  })

  it('readLedgityPpsFromLedgerMetadata reads pps_at_tx', () => {
    assert.equal(readLedgityPpsFromLedgerMetadata({ pps_at_tx: '1.02' }), '1.02')
  })
})
