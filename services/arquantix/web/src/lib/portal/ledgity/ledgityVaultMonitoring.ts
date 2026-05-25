import type { LedgityReconciliationStatus } from '@prisma/client'

import { checkBaseRpcHealth, type BaseRpcHealthSnapshot } from '@/lib/blockchain/baseRpcProvider'
import {
  getLedgityAlertMismatchToleranceRaw,
  getLedgityLiquidityWarningRatioBps,
  getLedgityReconciliationToleranceRaw,
} from '@/lib/portal/ledgity/ledgityReconciliationConfig'
import {
  isLedgityBetaEnabled,
  isLedgityDepositsDisabled,
  isLedgityVaultsEnabled,
  isLedgityWithdrawsDisabled,
  readLedgityLocalSandboxEnabledRaw,
} from '@/lib/portal/ledgity/ledgityConfig'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { getSandboxLedgityDependencyHealth } from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'

function absBigInt(value: bigint): bigint {
  return value < BigInt(0) ? -value : value
}

/** Compare ledger vs on-chain avec tolérance configurable. */
export function compareLedgityReconciliationAssets(args: {
  ledgerAssetsRaw: string | null
  onchainAssetsRaw: string | null
  toleranceRaw?: bigint
}): LedgityReconciliationStatus {
  const tolerance = args.toleranceRaw ?? getLedgityReconciliationToleranceRaw()
  const ledger = BigInt(args.ledgerAssetsRaw || '0')
  const onchain = BigInt(args.onchainAssetsRaw || '0')

  if (ledger === BigInt(0) && onchain === BigInt(0)) return 'matched'
  if (ledger > BigInt(0) && onchain === BigInt(0)) return 'missing_onchain'
  if (ledger === BigInt(0) && onchain > BigInt(0)) return 'missing_ledger'
  if (absBigInt(ledger - onchain) <= tolerance) return 'matched'
  return 'mismatch'
}

export function isSignificantLedgityMismatchDelta(deltaAssetsRaw: string | null | undefined): boolean {
  if (!deltaAssetsRaw) return false
  return absBigInt(BigInt(deltaAssetsRaw)) > getLedgityAlertMismatchToleranceRaw()
}

export function isLedgityLiquidityDeferred(args: {
  maxWithdrawRaw: bigint
  onchainAssetsRaw: bigint
  toleranceRaw?: bigint
}): boolean {
  const tolerance = args.toleranceRaw ?? getLedgityReconciliationToleranceRaw()
  if (args.onchainAssetsRaw <= BigInt(0)) return false
  return args.maxWithdrawRaw + tolerance < args.onchainAssetsRaw
}

export function isLedgityVaultLiquidityLow(args: {
  totalAssetsRaw: bigint
  trackedLedgerAssetsRaw: bigint
  ratioBps?: number
}): boolean {
  if (args.trackedLedgerAssetsRaw <= BigInt(0)) return false
  const ratioBps = args.ratioBps ?? getLedgityLiquidityWarningRatioBps()
  const threshold = (args.trackedLedgerAssetsRaw * BigInt(ratioBps)) / BigInt(10_000)
  return args.totalAssetsRaw < args.trackedLedgerAssetsRaw - threshold
}

export type LedgityDependencyHealth = {
  baseRpc: BaseRpcHealthSnapshot & { ok: boolean; latencyMs?: number; error?: string }
}

/** Ping RPC Base pour Ledgity (lecture ERC4626). */
export async function checkLedgityDependencyHealth(): Promise<LedgityDependencyHealth> {
  if (isLedgityLocalSandboxEnabled()) {
    return getSandboxLedgityDependencyHealth()
  }

  const startedRpc = Date.now()
  const baseRpcSnapshot = await checkBaseRpcHealth({ side: 'server' })
  const baseRpc: LedgityDependencyHealth['baseRpc'] = {
    ...baseRpcSnapshot,
    ok: baseRpcSnapshot.ok,
    latencyMs: baseRpcSnapshot.latencyMs ?? Date.now() - startedRpc,
    error: baseRpcSnapshot.error,
  }

  return { baseRpc }
}

export type LedgityAlertLevel = 'info' | 'warning' | 'critical'

export type LedgityGlobalStatus = 'healthy' | 'warning' | 'critical'

export type LedgityAlert = {
  code: string
  level: LedgityAlertLevel
  message: string
  count?: number
}

export function computeLedgityGlobalStatus(alerts: LedgityAlert[]): LedgityGlobalStatus {
  if (alerts.some((alert) => alert.level === 'critical')) return 'critical'
  if (alerts.some((alert) => alert.level === 'warning')) return 'warning'
  return 'healthy'
}

export function buildLedgityMonitoringAlerts(args: {
  pendingTransactionsCount: number
  pendingThresholdMinutes: number
  mismatchCount: number
  significantMismatchCount: number
  missingOnchainCount: number
  missingLedgerCount: number
  ppsUnavailableCount: number
  liquidityWarningCount: number
  vaultPausedCount: number
  withdrawalsPausedCount: number
  dependencyHealth: LedgityDependencyHealth
  sandboxEnabledInProd: boolean
}): LedgityAlert[] {
  const alerts: LedgityAlert[] = []

  if (args.sandboxEnabledInProd) {
    alerts.push({
      code: 'sandbox_enabled_in_prod',
      level: 'critical',
      message: 'LEDGITY_LOCAL_SANDBOX_ENABLED est actif en production — désactiver immédiatement.',
    })
  }

  if (!args.dependencyHealth.baseRpc.ok) {
    alerts.push({
      code: 'rpc_unavailable',
      level: 'critical',
      message: `RPC Base indisponible : ${args.dependencyHealth.baseRpc.error ?? 'erreur inconnue'}`,
    })
  } else if (args.dependencyHealth.baseRpc.publicRpcAsPrimary) {
    alerts.push({
      code: 'rpc_public_primary',
      level: 'critical',
      message: 'RPC public Base utilisé comme provider principal — configurer BASE_RPC_URL_PRIMARY.',
    })
  } else if (args.dependencyHealth.baseRpc.usedFallback) {
    alerts.push({
      code: 'rpc_failover',
      level: 'warning',
      message: `Failover RPC Base actif (provider : ${args.dependencyHealth.baseRpc.activeProvider ?? 'fallback'})`,
    })
  }

  if (args.ppsUnavailableCount > 0) {
    alerts.push({
      code: 'pps_unavailable',
      level: 'critical',
      message: `${args.ppsUnavailableCount} position(s) sans PPS / convertToAssets`,
      count: args.ppsUnavailableCount,
    })
  }

  if (args.vaultPausedCount > 0) {
    alerts.push({
      code: 'vault_paused',
      level: 'critical',
      message: `${args.vaultPausedCount} vault(s) Ledgity en pause`,
      count: args.vaultPausedCount,
    })
  }

  if (args.withdrawalsPausedCount > 0) {
    alerts.push({
      code: 'withdrawals_paused',
      level: 'critical',
      message: `${args.withdrawalsPausedCount} vault(s) avec retraits suspendus`,
      count: args.withdrawalsPausedCount,
    })
  }

  if (args.liquidityWarningCount > 0) {
    alerts.push({
      code: 'liquidity_low',
      level: args.liquidityWarningCount >= 3 ? 'critical' : 'warning',
      message: `${args.liquidityWarningCount} alerte(s) liquidité RWA / retrait différé`,
      count: args.liquidityWarningCount,
    })
  }

  if (args.pendingTransactionsCount > 0) {
    alerts.push({
      code: 'pending_tx_stale',
      level: args.pendingTransactionsCount >= 3 ? 'critical' : 'warning',
      message: `${args.pendingTransactionsCount} transaction(s) pending depuis plus de ${args.pendingThresholdMinutes} min`,
      count: args.pendingTransactionsCount,
    })
  }

  if (args.significantMismatchCount > 0) {
    alerts.push({
      code: 'ledger_onchain_mismatch',
      level: 'critical',
      message: `${args.significantMismatchCount} mismatch(es) ledger ↔ on-chain > seuil`,
      count: args.significantMismatchCount,
    })
  } else if (args.mismatchCount > 0) {
    alerts.push({
      code: 'ledger_onchain_mismatch_minor',
      level: 'warning',
      message: `${args.mismatchCount} mismatch(es) dans la tolérance`,
      count: args.mismatchCount,
    })
  }

  if (args.missingOnchainCount > 0) {
    alerts.push({
      code: 'missing_onchain',
      level: 'warning',
      message: `${args.missingOnchainCount} position(s) ledger sans équivalent on-chain`,
      count: args.missingOnchainCount,
    })
  }

  if (args.missingLedgerCount > 0) {
    alerts.push({
      code: 'missing_ledger',
      level: 'warning',
      message: `${args.missingLedgerCount} position(s) on-chain sans ledger`,
      count: args.missingLedgerCount,
    })
  }

  return alerts
}

export function getLedgityRuntimeModeSnapshot() {
  return {
    vaultsEnabled: isLedgityVaultsEnabled(),
    betaEnabled: isLedgityBetaEnabled(),
    depositsDisabled: isLedgityDepositsDisabled(),
    withdrawsDisabled: isLedgityWithdrawsDisabled(),
    sandboxEnabled: isLedgityLocalSandboxEnabled(),
    sandboxEnabledRaw: readLedgityLocalSandboxEnabledRaw(),
    mode: isLedgityLocalSandboxEnabled()
      ? 'sandbox'
      : isLedgityVaultsEnabled()
        ? 'live'
        : 'read_only',
  }
}

export function isLedgitySandboxEnabledInProduction(): boolean {
  return process.env.NODE_ENV === 'production' && readLedgityLocalSandboxEnabledRaw()
}
